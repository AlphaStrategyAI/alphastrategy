# Spent Session Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Name a persist-before-send session window as spent — even with zero fills — on halt copy, Clock Last, After halt, and help, without retrying or un-consuming the event.

**Architecture:** Snapshot `last_rebalance_complete` flips False at persist-before-send and True only when the rebalance finishes. Interrupted recovery halt reason appends `{last_rebalance_event} spent`. Clock Last paints `spent` from `GET /api/status`. Resume still does not catch up.

**Tech Stack:** Supervisor snapshot, Quiet cockpit JS/CSS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-spent-window-requirements.md`](../requirements/2026-08-20-alphastrategy-spent-window-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Do not retry remaining orders. Do not un-consume `last_rebalance_event`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/state.py`, `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/cli/main.py`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: 0-fill crash + resume**

In `tests/alphastrategy/test_halt_flatten.py`, after `test_restart_during_rebalancing_halts_without_duplicate_orders`, add:

```python
def test_restart_before_first_fill_spends_session_window(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.crash_after_place = 0
    supervisor = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    supervisor.start_sleeve("asb_test", 0.4)
    with pytest.raises(SimulatedCrash):
        _trigger_open_rebalance(tmp_path, broker, supervisor)

    inflight = _read_state(tmp_path)
    assert inflight["state"] == "rebalancing"
    assert inflight["last_rebalance_event"] == "2024-01-31:open"
    assert inflight["rebalance_placed"] == 0
    assert inflight["last_rebalance_complete"] is False
    assert inflight["orders_today"] == 0
    assert broker.orders == []

    restarted = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    reason = (restarted.snapshot.halt_reason or "").lower()
    assert restarted.state == SupervisorState.HALTED
    assert broker.close_all_called is False
    assert restarted.snapshot.rebalance_placed == 0
    assert restarted.snapshot.last_rebalance_event == "2024-01-31:open"
    assert restarted.snapshot.last_rebalance_complete is False
    assert "interrupted rebalancing" in reason
    assert "2024-01-31:open spent" in reason
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rebalances = [event for event in events if event["event"] == "rebalance"]
    assert rebalances[-1]["complete"] is False
    assert rebalances[-1]["orders"] == 0
    first = list(broker.orders)
    broker.advance_now(open_time + timedelta(minutes=10))
    restarted.tick()
    assert broker.orders == first
    restarted.resume()
    broker.advance_now(open_time + timedelta(minutes=11))
    restarted.tick()
    assert broker.orders == first
    assert restarted.snapshot.last_rebalance_event == "2024-01-31:open"
    assert restarted.snapshot.last_rebalance_complete is False
```

In `test_rebalance_persists_inflight_before_first_place` add:

```python
    assert broker.before_first["last_rebalance_complete"] is False
    assert finished["last_rebalance_complete"] is True
```

In `test_open_rebalance_places_orders_and_sets_last_event` add:

```python
    assert state["last_rebalance_complete"] is True
```

In `test_restart_during_rebalancing_halts_without_duplicate_orders` add:

```python
    assert "2024-01-31:open spent" in (restarted.snapshot.halt_reason or "").lower()
    assert restarted.snapshot.last_rebalance_complete is False
```

- [ ] **Step 2: API, CLI, JS, CSS, help**

`tests/alphastrategy/test_api.py` `test_status_includes_last_rebalance_and_countdown`: after the last_rebalance_event assert, add `assert body["last_rebalance_complete"] is True`.

`tests/alphastrategy/test_cli.py` `test_status_prints_json`: add `assert "last_rebalance_complete" in payload`.

`tests/alphastrategy/test_e2e_mocked.py` after `assert status["last_rebalance_event"] == "2024-01-31:open"` add `assert status["last_rebalance_complete"] is True`.

In `tests/alphastrategy/test_web_tokens.py` extend `test_js_paints_clock_continuity_tiles`:

```python
    assert "last_rebalance_complete" in paint
    assert '"spent"' in paint
    assert "warn" in paint
    assert "Gross cap" not in js_text
```

Add:

```python
def test_css_last_rebalance_spent_warn_token(css_text: str) -> None:
    last = re.search(r"#metric-last-rebalance\.warn\s*\{[^}]*\}", css_text)
    assert last is not None and "#f59e0b" in last.group(0).lower()
```

`REQUIRED_PHRASES` add `"Clock Last names the spent window"` and `"even with 0 fills"`.

- [ ] **Step 3: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_restart_before_first_fill_spends_session_window tests/alphastrategy/test_halt_flatten.py::test_rebalance_persists_inflight_before_first_place tests/alphastrategy/test_web_tokens.py::test_js_paints_clock_continuity_tiles tests/alphastrategy/test_web_tokens.py::test_css_last_rebalance_spent_warn_token tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_api.py::test_status_includes_last_rebalance_and_countdown tests/alphastrategy/test_cli.py::test_status_prints_json -q`

Expected: FAIL (`last_rebalance_complete` missing and/or spent copy absent).

---

### Task 2: Snapshot + recovery + status

- [ ] **Step 4: `SupervisorSnapshot`**

In `src/alphastrategy/supervisor/state.py` add `last_rebalance_complete: bool = True`. In `from_dict`:

```python
            last_rebalance_complete=bool(payload.get("last_rebalance_complete", True)),
```

`to_dict` already uses `asdict`.

- [ ] **Step 5: `_rebalance` / `_recover_interrupted_rebalance`**

In `_rebalance`, when `plans` is non-empty, set `last_rebalance_complete = False` next to the existing persist-before-send fields.

After a successful batch (`place_error is None`), set `last_rebalance_complete = True` before `_set_idle_state`. Zero-plan path also sets `True` with `last_rebalance_event`.

In `_recover_interrupted_rebalance`, set `last_rebalance_complete = False`. Halt:

```python
        marker = self._snapshot.last_rebalance_event or ""
        if marker:
            self._halt(f"interrupted rebalancing after {placed} orders; {marker} spent")
        else:
            self._halt(f"interrupted rebalancing after {placed} orders")
```

Do not change `_place_batch`. Do not retry. Do not clear `last_rebalance_event` on resume.

- [ ] **Step 6: API + CLI**

`handle_get_status` add `"last_rebalance_complete": bool(snapshot.last_rebalance_complete)`.

`src/alphastrategy/cli/main.py` offline status payload: the same key from the snapshot.

---

### Task 3: Clock Last + help

- [ ] **Step 7: paint + CSS**

In `src/alphastrategy/web/static/js/paint-portfolio.js` `renderSessionMetrics`, after resolving `last`:

```javascript
    if (lastEl) lastEl.classList.remove("warn");
    const last = state.status && state.status.last_rebalance_event;
    const complete = state.status && state.status.last_rebalance_complete;
    if (!last) {
      if (lastEl) lastEl.textContent = "—";
      if (lastSub) lastSub.textContent = "—";
    } else {
      const parts = String(last).split(":");
      const kind = parts.length > 1 ? parts.slice(1).join(":") : String(last);
      const date = parts.length > 1 ? parts[0] : "—";
      if (complete === false) {
        if (lastEl) {
          lastEl.textContent = "spent";
          lastEl.classList.add("warn");
        }
        if (lastSub) lastSub.textContent = kind;
      } else {
        if (lastEl) lastEl.textContent = kind;
        if (lastSub) lastSub.textContent = date;
      }
    }
```

Keep the existing `dashNowLast` helper for clock errors. Do not add a second `const reason` in `renderBanners`.

In `src/alphastrategy/web/static/styles.css` next to `#metric-session.open`:

```css
#metric-last-rebalance.warn {
  color: #f59e0b;
}
```

- [ ] **Step 8: help + README**

`execution` body, after the persist-before-send sentence, add: `Persist-before-send spends the session event even with 0 fills. Clock Last names the spent window.`

`how_portfolio` Clock sentence: add `Clock Last names the spent window when that event did not finish.`

`how_run` after `After halt shows the halt reason.`: add `After halt names the spent session event.`

README Operator persist-before-send bullet: add that persist-before-send spends the session event even with 0 fills, Clock Last names that spent window, and resume does not catch up.

- [ ] **Step 9: Full suite PASS.** Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass.

---
