# Caps LIMIT waits when a paper sleeve has no last weights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When any positive paper sleeve has no last sleeve weights, Caps LIMIT is `kind unknown` instead of replaying last combined or a partial combine, and the desk says the next send waits rather than flatten.

**Architecture:** `_next_send_ready(snapshot)` is true only when every `sleeves[id] > 0` has a non-empty `last_sleeve_weights[id]`, or there are no positive sleeves. `from_supervisor` sets `{reason: next_send_unknown, kind: unknown}` when not ready. Banner, Clock, CLI, and Book rail special-case `kind === "unknown"`. Book `check_book` still wins.

**Tech Stack:** Python 3.9+, pytest, cockpit JS parts, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-wait-weights-requirements.md`](../requirements/2026-08-21-alphastrategy-wait-weights-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET. Do not place.
- Keep Caps four tiles. Keep `#risk-cap-order`.
- Keep empty-`last_prices` last_combined 0.40 → `live_limit` null.
- Keep no-sleeves last_combined 0.18 Order size send LIMIT.
- Do not add `next_send_unknown` to `POLICY_LABELS`.
- `paint-portfolio.js` stays ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/cli/main.py`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_web_tokens.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_web_tokens.py`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add after the current-allocations phrase:

```python
    "Caps LIMIT waits when a paper sleeve has no last weights",
    "Clock Next is weights while a paper sleeve has no last weights",
```

In `test_api.py` after `test_status_live_limit_next_send_follows_current_allocation`:

```python
def test_status_live_limit_unknown_when_paper_sleeve_has_no_last_weights(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.set_policy({"max_order_notional_frac": 0.10})
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.18}
    supervisor.snapshot.last_sleeve_weights = {}
    supervisor.snapshot.sleeves = {"asb_y": 0.18}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "next_send_unknown"
    assert body["utilization"]["live_limit"]["kind"] == "unknown"
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["live_limit"]["reason"] == "next_send_unknown"
    assert risk["utilization"]["live_limit"]["kind"] == "unknown"
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"


def test_status_live_limit_unknown_when_one_paper_sleeve_missing_weights(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.set_policy({"max_order_notional_frac": 0.10})
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.18}
    supervisor.snapshot.last_sleeve_weights = {"asb_x": {"AAPL": 1.0}}
    supervisor.snapshot.sleeves = {"asb_x": 0.18, "asb_y": 0.01}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "next_send_unknown"
    assert body["utilization"]["live_limit"]["kind"] == "unknown"
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"


def test_status_book_limit_wins_over_unknown_next_send(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {"AAPL": 0.225}
    supervisor.snapshot.last_prices = {"AAPL": 150.0}
    supervisor.snapshot.last_sleeve_weights = {}
    supervisor.snapshot.sleeves = {"asb_y": 0.18}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 15.0}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "max_name_weight"
    assert body["utilization"]["live_limit"]["kind"] == "book"
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"
```

In `test_risk.py` after `test_from_supervisor_live_limit_next_send_follows_current_allocation`:

```python
def test_from_supervisor_live_limit_unknown_when_paper_sleeve_has_no_last_weights() -> None:
    from alphastrategy.risk.utilization import from_supervisor

    class Snap:
        orders_today = 0
        last_combined = {"AAPL": 0.18}
        last_got = {}
        last_prices = {"AAPL": 100.0}
        last_sleeve_weights = {}
        sleeves = {"asb_y": 0.18}

    class Fake:
        snapshot = Snap()

        def spoken_policy(self):
            return replace(AccountPolicy.defaults(), max_order_notional_frac=0.10)

        def live_book(self):
            return {"equity": 10_000.0, "cash": 10_000.0}, []

        def live_cap_weights(self, equity, positions):
            del equity, positions
            return {}

    out = from_supervisor(Fake(), live=True)
    assert out["live_limit"]["reason"] == "next_send_unknown"
    assert out["live_limit"]["kind"] == "unknown"
```

In `test_cli.py` after `test_status_prints_send_limit_on_stderr`:

```python
def test_status_prints_unknown_limit_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "idle_in_session",
        "clock": {},
        "halted": False,
        "flattened": False,
        "utilization": {
            "live_limit": {"reason": "next_send_unknown", "kind": "unknown"}
        },
        "heartbeat": {"age_seconds": 4, "pulse": "live", "interval_seconds": 20},
        "book": {"source": "heartbeat"},
        "pnl": 100.0,
        "pnl_source": "last_close",
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    out = json.loads(captured.out.strip())
    assert out["pnl"] == 100.0
    assert captured.err.splitlines() == [
        "BOOK: heartbeat",
        "PNL: 100.00 vs last close",
        "LIMIT: next send waits for last sleeve weights — Caps cannot dry-run",
    ]
    patch_alpaca.assert_not_called()
```

In `test_web_tokens.py` after `test_js_clock_next_flatten_while_live_limit`:

```python
def test_js_clock_next_weights_while_unknown_limit(js_text: str) -> None:
    session = js_text[
        js_text.find("function renderSessionMetrics") : js_text.find("function bookDrift")
    ]
    assert "weights · " in session
    assert 'kind === "unknown"' in session
    assert "flatten send · " in session
    assert "held · " in session
    assert "flat · " in session
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

After `test_js_paints_live_limit_banner`:

```python
def test_js_paints_unknown_limit_banner(js_text: str) -> None:
    rails = js_text[
        js_text.find("function renderLiveLimitBanner") : js_text.find("function paintBookLimitRail")
    ]
    assert "next send waits for last sleeve weights" in rails
    assert "Caps cannot dry-run" in rails
    assert 'kind === "unknown"' in rails
    assert "next rebalance will flatten" in rails
    banners = js_text[
        js_text.find("function renderBanners") : js_text.find("function renderPortfolio")
    ]
    assert banners.count("const reason") == 1
    assert "Gross cap" not in js_text
    assert "Order size" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

Keep `test_status_live_limit_next_send_order_size`.
Keep `test_from_supervisor_live_limit_ignores_last_combined`.
Keep `test_status_prints_pnl_on_stderr`.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_status_live_limit_unknown_when_paper_sleeve_has_no_last_weights tests/alphastrategy/test_api.py::test_status_live_limit_unknown_when_one_paper_sleeve_missing_weights tests/alphastrategy/test_api.py::test_status_book_limit_wins_over_unknown_next_send tests/alphastrategy/test_risk.py::test_from_supervisor_live_limit_unknown_when_paper_sleeve_has_no_last_weights tests/alphastrategy/test_api.py::test_status_live_limit_next_send_order_size tests/alphastrategy/test_risk.py::test_from_supervisor_live_limit_ignores_last_combined tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_cli.py::test_status_prints_unknown_limit_on_stderr tests/alphastrategy/test_web_tokens.py::test_js_clock_next_weights_while_unknown_limit tests/alphastrategy/test_web_tokens.py::test_js_paints_unknown_limit_banner -q
```

Expected: new live_limit tests fail (`kind == send` or `reason == max_order_notional_frac` — last combined / partial combine). Help phrases missing. CLI unknown line missing. JS `weights · ` missing. Existing Order size / empty-prices tests still pass. Book-wins test may already pass (book LIMIT already wins) — if it passes, keep it as a lock.

- [ ] **Step 3: Commit tests and docs**

```bash
git add docs/requirements/2026-08-21-alphastrategy-wait-weights-requirements.md docs/plans/2026-08-21-alphastrategy-wait-weights-technical-design.md tests/alphastrategy/test_api.py tests/alphastrategy/test_risk.py tests/alphastrategy/test_helptext.py tests/alphastrategy/test_cli.py tests/alphastrategy/test_web_tokens.py
git commit -m "test: Caps LIMIT waits when a paper sleeve has no last weights"
```

---

### Task 2: Implement

- [ ] **Step 4: `_next_send_ready` in utilization.py**

After `_next_send_combined`:

```python
def _next_send_ready(snapshot: Any) -> bool:
    weights = getattr(snapshot, "last_sleeve_weights", None) or {}
    sleeves = getattr(snapshot, "sleeves", None) or {}
    for bundle_id, raw_alloc in sleeves.items():
        try:
            alloc = float(raw_alloc or 0)
        except (TypeError, ValueError):
            continue
        if alloc <= 0:
            continue
        sleeve_weights = weights.get(bundle_id)
        if not isinstance(sleeve_weights, dict) or not sleeve_weights:
            return False
    return True
```

`from_supervisor` dry-run:

```python
    if live and out.get("live_limit") is None:
        if not _next_send_ready(snapshot):
            out["live_limit"] = {"reason": "next_send_unknown", "kind": "unknown"}
        else:
            out["live_limit"] = _next_send_limit(
                policy=supervisor.spoken_policy(),
                combined=_next_send_combined(snapshot),
                prices=getattr(snapshot, "last_prices", None),
                positions=positions,
                equity=equity,
                orders_today=snapshot.orders_today,
            )
    return out
```

Do not flatten. Do not call DSL. Do not add `POLICY_LABELS` keys.

- [ ] **Step 5: CLI, banner, Clock, Book rail**

`src/alphastrategy/cli/main.py` after `_LIMIT_SEND_STATUS`:

```python
_LIMIT_UNKNOWN_STATUS = (
    "LIMIT: next send waits for last sleeve weights — Caps cannot dry-run"
)
```

`_status_limit_line`:

```python
    if limit.get("kind") == "unknown":
        return _LIMIT_UNKNOWN_STATUS
    template = _LIMIT_SEND_STATUS if limit.get("kind") == "send" else _LIMIT_STATUS
    return template.format(label=label_for(str(reason)))
```

`paint-rails.js` `renderLiveLimitBanner` after the hidden/return for missing limit:

```javascript
    el.classList.remove("hidden");
    if (limit.kind === "unknown") {
      el.textContent =
        "LIMIT: next send waits for last sleeve weights — Caps cannot dry-run";
      return;
    }
    const through =
      limit.kind === "send" ? "next send through " : "live book through ";
    el.textContent =
      "LIMIT: " + through + policyLabel(limit.reason) + " — next rebalance will flatten";
```

`paintBookLimitRail` warn line:

```javascript
    if (limit && limit.reason && limit.kind !== "unknown") band.classList.add("warn");
```

`paint-portfolio.js` Clock live_limit branch (keep file ≤ 400 lines):

```javascript
      } else if (
        utilization().live_limit &&
        utilization().live_limit.reason
      ) {
        countEl.classList.add("warn");
        const k = utilization().live_limit.kind;
        const prefix =
          k === "unknown" ? "weights · " : k === "send" ? "flatten send · " : "flatten · ";
        kindEl.textContent = prefix + kind;
      } else {
```

- [ ] **Step 6: Help and README**

`helptext.py`: add `Caps LIMIT waits when a paper sleeve has no last weights. ` to `execution` (after Caps LIMIT current allocations), `halt_flatten` (same), `how_risk` (same). Add `Clock Next is weights while a paper sleeve has no last weights. ` to `halt_flatten` after Clock Next flatten send.

README Operator: Caps sentence after Caps LIMIT current allocations. Clock sentence after Clock Next flatten send. Keep `Next rebalance`.

- [ ] **Step 7: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 8: Commit, push, update PR**

```bash
git add src/alphastrategy/risk/utilization.py src/alphastrategy/cli/main.py src/alphastrategy/web/static/js/paint-rails.js src/alphastrategy/web/static/js/paint-portfolio.js src/alphastrategy/helptext.py README.md
git commit -m "feat: Caps LIMIT waits when a paper sleeve has no last weights"
```
