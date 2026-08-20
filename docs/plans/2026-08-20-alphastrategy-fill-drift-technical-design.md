# Fill vs Mark Book Drift Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Book Drift and the execution-deviation banner follow last-fill weights; Positions Got / Cap keep live marks from heartbeat prices.

**Architecture:** Persist `last_fill_got` only from `_snapshot_got`. Heartbeat continues to mark `last_got`. Portfolio rows expose `fill` plus `weight`. JS `bookDrift` gaps wanted vs fill.

**Tech Stack:** Supervisor snapshot, portfolio API, Quiet cockpit JS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-fill-drift-requirements.md`](../requirements/2026-08-20-alphastrategy-fill-drift-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. Do not spend a session event on a heartbeat.
- Each `js/` part stays ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/state.py`, `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add `"Book Drift follows the last fill, not last prices"`.

In `tests/alphastrategy/test_halt_flatten.py` after `test_heartbeat_does_not_flatten_when_live_name_breaches_cap`:

```python
def test_open_rebalance_writes_last_fill_got(tmp_path: Path) -> None:
    _open_time, _session_close, broker, supervisor = _open_then_idle(tmp_path)
    assert broker.positions.get("AAPL") == pytest.approx(15.0)
    assert supervisor.snapshot.last_got["AAPL"] == pytest.approx(0.15)
    assert supervisor.snapshot.last_fill_got["AAPL"] == pytest.approx(0.15)


def test_heartbeat_marks_do_not_overwrite_last_fill_got(tmp_path: Path) -> None:
    open_time, _session_close, broker, supervisor = _open_then_idle(tmp_path)
    assert supervisor.snapshot.last_fill_got["AAPL"] == pytest.approx(0.15)
    broker.bars["AAPL"] = {"bars": [{"c": 150.0, "t": "2024-01-31"}]}
    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()
    assert supervisor.snapshot.last_got["AAPL"] == pytest.approx(0.225)
    assert supervisor.snapshot.last_fill_got["AAPL"] == pytest.approx(0.15)
    disk = _read_state(tmp_path)
    assert disk["last_got"]["AAPL"] == pytest.approx(0.225)
    assert disk["last_fill_got"]["AAPL"] == pytest.approx(0.15)
```

In `test_flatten_clears_last_book_and_zeros_sleeves` after `assert snap.last_got == {}` add `assert snap.last_fill_got == {}`.

In `tests/alphastrategy/test_api.py` after `test_portfolio_includes_wanted_name_with_no_fill`:

```python
def test_portfolio_fill_stays_on_last_rebalance_after_mark(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_combined = {"AAPL": 0.15}
    supervisor.snapshot.last_prices = {"AAPL": 150.0}
    supervisor.snapshot.last_got = {"AAPL": 0.225}
    supervisor.snapshot.last_fill_got = {"AAPL": 0.15}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 15.0}
    broker.equity = 10_000.0
    body = client.get("/api/portfolio").json()
    pos = next(item for item in body["positions"] if item["symbol"] == "AAPL")
    assert pos["weight"] == pytest.approx(0.225)
    assert pos["fill"] == pytest.approx(0.15)
    assert pos["wanted"] == pytest.approx(0.15)
```

In `tests/alphastrategy/test_web_tokens.py` after `test_js_deviation_banner_follows_book_drift`:

```python
def test_js_book_drift_uses_fill_not_mark(js_text: str) -> None:
    fn = js_text[
        js_text.find("function bookDrift") : js_text.find("function renderBookDrift")
    ]
    assert "pos.fill" in fn
    assert "pos.wanted" in fn
    rails = js_text[
        js_text.find("function wantedGotBar") : js_text.find("function paintUtilTrack")
    ]
    assert "fill" in rails
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
    banners = js_text[
        js_text.find("function renderBanners") : js_text.find("function renderPortfolio")
    ]
    assert banners.count("const reason") == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_halt_flatten.py::test_open_rebalance_writes_last_fill_got \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_marks_do_not_overwrite_last_fill_got \
  tests/alphastrategy/test_halt_flatten.py::test_flatten_clears_last_book_and_zeros_sleeves \
  tests/alphastrategy/test_api.py::test_portfolio_fill_stays_on_last_rebalance_after_mark \
  tests/alphastrategy/test_web_tokens.py::test_js_book_drift_uses_fill_not_mark \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL on missing `last_fill_got`, missing `fill`, JS still gapping `pos.weight`, help phrase missing.

If `test_flatten_clears_last_book_and_zeros_sleeves` PASSES except the new `last_fill_got` assert, keep the existing asserts.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-fill-drift-requirements.md \
  docs/plans/2026-08-20-alphastrategy-fill-drift-technical-design.md \
  tests/alphastrategy/test_halt_flatten.py tests/alphastrategy/test_api.py \
  tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_helptext.py
git commit -m "test: Book Drift follows last fill after heartbeat marks"
```

---

### Task 2: Snapshot, heartbeat, portfolio, paint, help

- [ ] **Step 1: Persist `last_fill_got`**

In `SupervisorSnapshot` add `last_fill_got: dict[str, float] = field(default_factory=dict)` next to `last_got`. In `from_dict` load it like `last_got`.

`_snapshot_got`: after `self._snapshot.last_got = dict(got)` also `self._snapshot.last_fill_got = dict(got)`.

Heartbeat block: do **not** assign `last_fill_got`.

`_flatten_account`: `self._snapshot.last_fill_got = {}` next to `last_got`.

- [ ] **Step 2: Portfolio `fill`**

`_enrich_positions(..., last_fill_got=None)`. For live and wanted-only rows, if `symbol in (last_fill_got or {})`: `item["fill"] = float(last_fill_got[symbol])`.

`handle_get_portfolio` passes `snapshot.last_fill_got`.

- [ ] **Step 3: JS**

`bookDrift`: gap `wanted` vs `pos.fill` when `fill` is not null/undefined, else `pos.weight`.

`wantedGotBar(wanted, got, cap, fill)`: size from `got`; `drift` class from wanted vs fill (fallback got).

Positions table: `wantedGotBar(pos.wanted, pos.weight, cap, pos.fill)`.

- [ ] **Step 4: Help / README**

Cockpit Book Drift sentence and `how_portfolio`: `Book Drift follows the last fill, not last prices.`

`task_wanted`: Got is the current mark. Book Drift follows the last fill, not last prices.

README Positions / Book Drift line: same.

- [ ] **Step 5: Run targeted tests, then full `tests/alphastrategy/`**

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: Book Drift follows last fill; Got stays the live mark"
```
