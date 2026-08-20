# Operator Desk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (this cycle explicitly chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the v1 Quiet cockpit gaps so the paper desk shows next-rebalance countdown, last sleeve contribution, `stopped` state, an Activity blotter with drill-in, a visible control-plane failure, preserved Risk forms, and a louder account flatten confirm.

**Architecture:** Add a pure countdown helper beside the existing clock rules. Persist last book and `stopped` on `SupervisorSnapshot`. Expose those fields on the existing JSON API. Update the static cockpit; replace `cgi.FieldStorage` with a stdlib multipart parser. Do not change halt/flatten, session times, or live walls.

**Tech Stack:** Python 3.9+, pytest, stdlib HTTP, hand-authored HTML/CSS/JS. Tests mock the broker; they never hit Alpaca.

**Requirements:** [`docs/requirements/2026-08-19-alphastrategy-operator-desk-requirements.md`](../requirements/2026-08-19-alphastrategy-operator-desk-requirements.md)

## Global Constraints

- Package `alphastrategy`, CLI `alphastrategy`, paper-only v1 walls unchanged.
- Do not grow `src/openstrategy/` as the product.
- Supervisor remains the only order placer. Heartbeat does not place orders. Resume does not catch-up rebalance.
- Quiet cockpit tokens stay `#0b0e14` / `#11151d` / `#2a3142` / `#e5e9f0` / `#5c6573` / `#9ba3b4` / `#10b981` / `#f59e0b` / `#ef4444`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never place a real order.
- Contribution after Stop stays at last rebalance until the next legal rebalance (do not recompute from current allocation).
- Account kill confirm is Web-only (`FLATTEN`); API/CLI verbs stay explicit without a typed phrase.

## File map

- Modify: `src/alphastrategy/supervisor/clock.py` — `RebalanceCountdown`, `rebalance_countdown`
- Modify: `src/alphastrategy/supervisor/state.py` — persist last book + `stopped`
- Modify: `src/alphastrategy/supervisor/loop.py` — record book on rebalance; `stopped` on start/stop
- Modify: `src/alphastrategy/api/handlers.py` — status/portfolio/bundles fields; multipart without `cgi`
- Modify: `src/alphastrategy/web/static/index.html`, `app.js`, `styles.css`
- Test: `tests/alphastrategy/test_clock.py`, `test_halt_flatten.py`, `test_api.py`, `test_web_tokens.py`, `test_e2e_mocked.py`
- Create: `tests/alphastrategy/test_multipart.py`

---

### Task 1: Rebalance countdown helper

**Files:**
- Modify: `src/alphastrategy/supervisor/clock.py`
- Test: `tests/alphastrategy/test_clock.py`

**Interfaces:**
- Consumes: existing `ClockSnapshot(is_open, next_open, next_close, now)`
- Produces: `RebalanceCountdown(next_rebalance: str, at: datetime, seconds: int)` and `rebalance_countdown(cur: ClockSnapshot, last_event: str | None) -> RebalanceCountdown`

- [ ] **Step 1: Write the failing tests**

Append to `tests/alphastrategy/test_clock.py`:

```python
from alphastrategy.supervisor.clock import rebalance_countdown


def test_countdown_closed_market_is_open_plus_three_minutes():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    now = open_time - timedelta(minutes=30)
    cur = _snap(False, open_time, session_close, now)
    hint = rebalance_countdown(cur, None)
    assert hint.next_rebalance == "open"
    assert hint.at == open_time + timedelta(minutes=3)
    assert hint.seconds == int((hint.at - now).total_seconds())


def test_countdown_after_session_open_event_is_close_minus_twelve():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    now = datetime(2024, 1, 31, 16, 0)
    cur = _snap(True, datetime(2024, 2, 1, 14, 30), session_close, now)
    hint = rebalance_countdown(cur, "2024-01-31:open")
    assert hint.next_rebalance == "close"
    assert hint.at == session_close - timedelta(minutes=12)
    assert hint.seconds == int((hint.at - now).total_seconds())


def test_countdown_inside_close_window_has_zero_seconds():
    session_close = datetime(2024, 1, 31, 21, 0)
    now = session_close - timedelta(minutes=5)
    cur = _snap(True, datetime(2024, 2, 1, 14, 30), session_close, now)
    hint = rebalance_countdown(cur, "2024-01-31:open")
    assert hint.next_rebalance == "close"
    assert hint.seconds == 0


def test_countdown_after_close_event_is_next_open_plus_three():
    session_close = datetime(2024, 1, 31, 21, 0)
    next_open = datetime(2024, 2, 1, 14, 30)
    now = datetime(2024, 1, 31, 20, 55)
    cur = _snap(True, next_open, session_close, now)
    hint = rebalance_countdown(cur, "2024-01-31:close")
    assert hint.next_rebalance == "open"
    assert hint.at == next_open + timedelta(minutes=3)


def test_countdown_open_pending_when_open_not_recorded_is_due_now():
    session_close = datetime(2024, 1, 31, 21, 0)
    now = datetime(2024, 1, 31, 16, 0)
    cur = _snap(True, datetime(2024, 2, 1, 14, 30), session_close, now)
    hint = rebalance_countdown(cur, None)
    assert hint.next_rebalance == "open"
    assert hint.at == now
    assert hint.seconds == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_clock.py::test_countdown_closed_market_is_open_plus_three_minutes -v`

Expected: FAIL with `ImportError` or `rebalance_countdown` not defined.

- [ ] **Step 3: Write minimal implementation**

Add to `src/alphastrategy/supervisor/clock.py`:

```python
@dataclass(frozen=True)
class RebalanceCountdown:
    next_rebalance: str
    at: datetime
    seconds: int


def rebalance_countdown(
    cur: ClockSnapshot,
    last_event: str | None,
) -> RebalanceCountdown:
    session_date = cur.next_close.date().isoformat()
    open_key = f"{session_date}:open"
    close_key = f"{session_date}:close"
    now = cur.now

    def pack(kind: str, at: datetime) -> RebalanceCountdown:
        delta = (at - now).total_seconds()
        return RebalanceCountdown(kind, at, max(0, int(delta)))

    if not cur.is_open:
        return pack("open", cur.next_open + timedelta(minutes=3))
    if last_event == close_key:
        return pack("open", cur.next_open + timedelta(minutes=3))
    if last_event == open_key:
        return pack("close", cur.next_close - timedelta(minutes=12))
    return pack("open", now)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_clock.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/supervisor/clock.py tests/alphastrategy/test_clock.py
git commit -m "feat: add next-rebalance countdown helper"
```

---

### Task 2: Persist last book and stopped sleeves

**Files:**
- Modify: `src/alphastrategy/supervisor/state.py`
- Modify: `src/alphastrategy/supervisor/loop.py`
- Test: `tests/alphastrategy/test_halt_flatten.py`

**Interfaces:**
- Consumes: `combine`, `_collect_sleeves`, `_rebalance`, `start_sleeve`, `stop_sleeve`
- Produces: `SupervisorSnapshot` fields `last_combined: dict[str, float]`, `last_sleeve_weights: dict[str, dict[str, float]]`, `last_sleeve_contribution: dict[str, dict[str, float]]`, `last_prices: dict[str, float]`, `stopped: list[str]`

- [ ] **Step 1: Write the failing tests**

Append to `tests/alphastrategy/test_halt_flatten.py` (reuse `FakeBroker` and home fixtures already in that file):

```python
def test_stop_sleeve_is_listed_as_stopped(tmp_path: Path):
    home = AlphaStrategyHome(root=tmp_path)
    bundle_dir = home.imported_dir() / "asb_test"
    bundle_dir.mkdir(parents=True)
    broker = FakeBroker()
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.start_sleeve("asb_test", 0.4)
    supervisor.stop_sleeve("asb_test")
    assert "asb_test" in supervisor.snapshot.stopped
    assert supervisor.snapshot.sleeves["asb_test"] == 0.0


def test_start_sleeve_clears_stopped(tmp_path: Path):
    home = AlphaStrategyHome(root=tmp_path)
    (home.imported_dir() / "asb_test").mkdir(parents=True)
    supervisor = Supervisor(
        home=home,
        broker=FakeBroker(),
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.start_sleeve("asb_test", 0.4)
    supervisor.stop_sleeve("asb_test")
    supervisor.start_sleeve("asb_test", 0.2)
    assert "asb_test" not in supervisor.snapshot.stopped
    assert supervisor.snapshot.sleeves["asb_test"] == 0.2


def test_rebalance_persists_contribution_and_stop_does_not_zero_it(tmp_path: Path):
    home = AlphaStrategyHome(root=tmp_path)
    (home.imported_dir() / "asb_test").mkdir(parents=True)
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.bars["AAPL"] = {"bars": [{"c": 100.0, "t": "2024-01-31"}]}
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.start_sleeve("asb_test", 0.4)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    assert supervisor.snapshot.last_combined == {"AAPL": 0.4}
    assert supervisor.snapshot.last_sleeve_contribution["asb_test"]["AAPL"] == pytest.approx(0.4)
    assert supervisor.snapshot.last_prices["AAPL"] == pytest.approx(100.0)
    supervisor.stop_sleeve("asb_test")
    assert supervisor.snapshot.last_sleeve_contribution["asb_test"]["AAPL"] == pytest.approx(0.4)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_stop_sleeve_is_listed_as_stopped tests/alphastrategy/test_halt_flatten.py::test_rebalance_persists_contribution_and_stop_does_not_zero_it -v`

Expected: FAIL (`stopped` / `last_combined` missing).

- [ ] **Step 3: Write minimal implementation**

Update `SupervisorSnapshot` in `state.py`:

```python
last_combined: dict[str, float] = field(default_factory=dict)
last_sleeve_weights: dict[str, dict[str, float]] = field(default_factory=dict)
last_sleeve_contribution: dict[str, dict[str, float]] = field(default_factory=dict)
last_prices: dict[str, float] = field(default_factory=dict)
stopped: list[str] = field(default_factory=list)
```

In `from_dict`, load those keys with empty defaults. `to_dict` already uses `asdict`.

In `loop.py`:

- `start_sleeve`: after setting allocation, `self._snapshot.stopped = [b for b in self._snapshot.stopped if b != bundle_id]`
- `stop_sleeve`: set allocation 0 if present; if `bundle_id` is in sleeves, append to `stopped` if missing
- Change `_collect_sleeves` to return `list[tuple[str, float, dict[str, float]]]` (bundle id first). Update `_rebalance`:

```python
collected = self._collect_sleeves()
sleeves = [(alloc, weights) for _bid, alloc, weights in collected]
combined = combine(sleeves)
self._snapshot.last_sleeve_weights = {bid: dict(weights) for bid, _a, weights in collected}
self._snapshot.last_sleeve_contribution = {
    bid: {asset: alloc * weight for asset, weight in weights.items()}
    for bid, alloc, weights in collected
}
self._snapshot.last_combined = dict(combined)
# after prices = self._fetch_prices(...)
self._snapshot.last_prices = dict(prices)
```

Keep `_validate_weights` / `check_book` on implied notionals as today.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py tests/alphastrategy/test_e2e_mocked.py -q`

Expected: PASS (existing e2e still constructs `SupervisorSnapshot` with defaults).

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/supervisor/state.py src/alphastrategy/supervisor/loop.py tests/alphastrategy/test_halt_flatten.py
git commit -m "feat: persist last book and stopped sleeves"
```

---

### Task 3: Expose countdown, contribution, and stopped on the API

**Files:**
- Modify: `src/alphastrategy/api/handlers.py`
- Test: `tests/alphastrategy/test_api.py`

**Interfaces:**
- Consumes: `rebalance_countdown`, `supervisor.snapshot`
- Produces: `GET /api/status` adds `last_rebalance_event` and `countdown` (or `countdown: null` if clock is an error object). `GET /api/portfolio` adds `last_combined`, `sleeve_contribution`, `last_rebalance_event`, and position `notional`/`weight` when `last_prices` has the symbol. `GET /api/bundles` adds `stopped`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/alphastrategy/test_api.py`:

```python
from alphastrategy.supervisor.clock import ClockSnapshot, rebalance_countdown
from alphastrategy.supervisor.state import SupervisorState


def test_status_includes_last_rebalance_and_countdown(api_stack):
    client, _home, supervisor, broker = api_stack
    supervisor.snapshot.last_rebalance_event = "2024-01-31:open"
    broker._is_open = True
    response = client.get("/api/status")
    assert response.status == 200
    body = response.json()
    assert body["last_rebalance_event"] == "2024-01-31:open"
    clock = body["clock"]
    cur = ClockSnapshot(
        is_open=bool(clock["is_open"]),
        next_open=datetime.fromisoformat(clock["next_open"]),
        next_close=datetime.fromisoformat(clock["next_close"]),
        now=datetime.fromisoformat(clock["timestamp"]),
    )
    expected = rebalance_countdown(cur, "2024-01-31:open")
    assert body["countdown"]["next_rebalance"] == expected.next_rebalance
    assert body["countdown"]["seconds"] == expected.seconds
    assert "at" in body["countdown"]


def test_status_countdown_null_when_clock_fails(api_stack):
    client, _home, supervisor, broker = api_stack

    def boom():
        raise RuntimeError("clock down")

    broker.get_clock = boom  # type: ignore[method-assign]
    body = client.get("/api/status").json()
    assert "error" in body["clock"]
    assert body["countdown"] is None


def test_portfolio_includes_contribution_and_position_weight(api_stack):
    client, _home, supervisor, broker = api_stack
    supervisor.snapshot.last_combined = {"AAPL": 0.4}
    supervisor.snapshot.last_sleeve_contribution = {"asb_x": {"AAPL": 0.4}}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor.snapshot.last_rebalance_event = "2024-01-31:open"
    broker.positions = {"AAPL": 10.0}
    broker.equity = 10_000.0
    body = client.get("/api/portfolio").json()
    assert body["last_combined"] == {"AAPL": 0.4}
    assert body["sleeve_contribution"]["asb_x"]["AAPL"] == 0.4
    assert body["last_rebalance_event"] == "2024-01-31:open"
    pos = next(p for p in body["positions"] if p["symbol"] == "AAPL")
    assert pos["qty"] == 10.0 or pos["qty"] == "10.0" or float(pos["qty"]) == 10.0
    assert pos["notional"] == pytest.approx(1000.0)
    assert pos["weight"] == pytest.approx(0.1)


def test_bundles_lists_stopped(api_stack):
    client, home, supervisor, _broker = api_stack
    supervisor.start_sleeve("asb_x", 0.25)
    supervisor.stop_sleeve("asb_x")
    body = client.get("/api/bundles").json()
    assert "asb_x" in body["stopped"]
    assert "asb_x" not in body["paper"]
```

Note: `handle_get_portfolio` currently returns broker position dicts unchanged (`qty` as str). Tests should `float(pos["qty"])`. Add `notional` and `weight` as floats on each position dict without dropping `symbol`/`qty`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_status_includes_last_rebalance_and_countdown tests/alphastrategy/test_api.py::test_bundles_lists_stopped -v`

Expected: FAIL (missing keys).

- [ ] **Step 3: Write minimal implementation**

In `handlers.py`:

```python
from alphastrategy.supervisor.clock import ClockSnapshot, rebalance_countdown
from alphastrategy.supervisor.loop import _clock_snapshot, _parse_clock_dt  # prefer a tiny public helper if importing privates is ugly
```

Do **not** import loop privates if it creates a cycle. Parse clock in the handler:

```python
def _countdown_payload(clock: dict[str, Any], last_event: str | None) -> dict[str, Any] | None:
    if not isinstance(clock, dict) or clock.get("error") is not None:
        return None
    try:
        now_raw = clock.get("timestamp") or clock.get("now")
        cur = ClockSnapshot(
            is_open=bool(clock.get("is_open", False)),
            next_open=_parse_iso(clock["next_open"]),
            next_close=_parse_iso(clock["next_close"]),
            now=_parse_iso(now_raw),
        )
    except (KeyError, TypeError, ValueError):
        return None
    hint = rebalance_countdown(cur, last_event)
    return {
        "next_rebalance": hint.next_rebalance,
        "at": hint.at.isoformat(),
        "seconds": hint.seconds,
    }
```

Add `_parse_iso` in handlers (copy the `Z` → `+00:00` logic from `loop._parse_clock_dt`) rather than exporting loop internals.

`handle_get_status`: include `last_rebalance_event=snapshot.last_rebalance_event` and `countdown=_countdown_payload(clock, snapshot.last_rebalance_event)`.

`handle_get_portfolio`: include `last_combined`, `sleeve_contribution=snapshot.last_sleeve_contribution`, `last_rebalance_event`. Map positions:

```python
def _enrich_positions(positions: list[dict], equity: float, prices: dict[str, float]) -> list[dict]:
    out = []
    for pos in positions:
        item = dict(pos)
        symbol = str(item.get("symbol", ""))
        qty = float(item.get("qty", 0) or 0)
        price = prices.get(symbol)
        if price is not None:
            notional = qty * price
            item["notional"] = notional
            item["weight"] = (notional / equity) if equity else 0.0
        out.append(item)
    return out
```

`handle_get_bundles`: `"stopped": list(snapshot.stopped)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/api/handlers.py tests/alphastrategy/test_api.py
git commit -m "feat: expose countdown, contribution, and stopped on API"
```

---

### Task 4: Quiet cockpit operator desk

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`
- Modify: `src/alphastrategy/web/static/app.js`
- Modify: `src/alphastrategy/web/static/styles.css`
- Test: `tests/alphastrategy/test_web_tokens.py`

**Interfaces:**
- Consumes: `/api/status.countdown`, `/api/portfolio.sleeve_contribution`, `/api/bundles.stopped`, `/api/activity` array
- Produces: countdown clock line; contribution column; `stopped` state; blotter rows with expand; `#control-plane-banner`; risk-form dirty skip; account kill requires checkbox + typed `FLATTEN`

- [ ] **Step 1: Write the failing tests**

Append to `tests/alphastrategy/test_web_tokens.py`:

```python
@pytest.fixture
def js_text() -> str:
    return JS_PATH.read_text(encoding="utf-8")


def test_html_has_control_plane_banner(html_text: str) -> None:
    assert 'id="control-plane-banner"' in html_text
    assert 'id="account-kill-phrase"' in html_text
    assert 'id="account-kill-confirm"' in html_text
    assert "Contribution" in html_text
    assert "Notional" in html_text
    assert "Weight" in html_text


def test_js_renders_countdown_and_stopped(js_text: str) -> None:
    assert "countdown" in js_text
    assert "fmtCountdown" in js_text
    assert "sleeve_contribution" in js_text
    assert '"stopped"' in js_text or "stopped" in js_text
    assert "FLATTEN" in js_text
    assert "control-plane-banner" in js_text
    assert "riskFormIsDirty" in js_text
    assert "activity-detail" in js_text or "expanded" in js_text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_has_control_plane_banner -v`

Expected: FAIL (missing ids).

- [ ] **Step 3: Write minimal implementation**

HTML:

- After halt/deviation banners, add `<div id="control-plane-banner" class="banner fail hidden" role="alert"></div>`
- Positions thead: Symbol, Qty, Notional, Weight
- Sleeves thead: Bundle, Allocation, Contribution
- Account panel: checkbox `id="account-kill-confirm"` labelled “I understand this flattens the whole paper account”, text input `id="account-kill-phrase"` placeholder `FLATTEN`, then the existing kill button
- Activity list stays `#activity-list`

CSS: `.activity-list li.expanded .activity-detail { display: block; }` and `.activity-detail { display: none; white-space: pre-wrap; color: #9ba3b4; }` plus `.activity-list li { cursor: pointer; }`

JS (keep Quiet cockpit; no new colors):

- `fmtCountdown(seconds)` → `H:MM:SS` if hours else `MM:SS`
- Clock line: `Market OPEN · next close rebalance 01:23:45 at 2024-01-31T20:48:00 · now ...` using `status.countdown`
- Positions rows include notional/weight via `fmtNum` / `fmtPct`
- Sleeves rows: contribution from `portfolio.sleeve_contribution[id]` as `AAPL 40.0%` joined by ` · `, or `—`
- `sleeveState`: `stopped` if `bundles.stopped` includes id, or `status.state === "stopped"` and id is not import-only (in paper, stopped, or was paper). Exact: if `(bundles.stopped || []).includes(bundleId)` → `stopped`; else if `status.state === "stopped"` and `(bundles.paper[bundleId] || alloc history)` — use: if state is `stopped` and id is in `Object.keys(bundles.paper)` or `stopped` list or `portfolio.sleeves`; if only imported, stay `imported`. Simpler rule from spec: `stopped` if id in `stopped` OR (`status.state === "stopped"` AND id has allocation key in `portfolio.sleeves`). `halted` if alloc>0 and halted. `paper` if alloc>0. else `imported`.
- Activity: newest first; `li` with summary; click toggles `.expanded` and only one open
- `refresh()` on success hides control-plane banner; on catch shows `CONTROL PLANE: refresh failed`
- `renderRisk`: if `riskFormIsDirty()` only refresh `#risk-account-caps`, return
- Account kill click: require checkbox and `phrase === "FLATTEN"`

Empty contribution colspan 3. Positions empty colspan 4.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_api.py::test_get_root_returns_html tests/alphastrategy/test_api.py::test_get_static_assets -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/web/static tests/alphastrategy/test_web_tokens.py
git commit -m "feat: quiet cockpit countdown, blotter, and flatten confirm"
```

---

### Task 5: Multipart import without cgi

**Files:**
- Modify: `src/alphastrategy/api/handlers.py`
- Create: `tests/alphastrategy/test_multipart.py`

**Interfaces:**
- Consumes: raw `Content-Type` + body bytes
- Produces: `parse_multipart_file(content_type: str, body: bytes) -> tuple[str, bytes]` raising `ValueError` on missing file part. `_extract_upload` uses it. No `import cgi`.

- [ ] **Step 1: Write the failing tests**

Create `tests/alphastrategy/test_multipart.py`:

```python
from pathlib import Path

import pytest

from alphastrategy.api.handlers import parse_multipart_file


def test_parse_multipart_file_reads_named_part():
    boundary = "----alphastrategy-test"
    payload = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="gold.asb"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
        "ABC123"
        f"\r\n--{boundary}--\r\n"
    ).encode("utf-8")
    filename, data = parse_multipart_file(
        f"multipart/form-data; boundary={boundary}",
        payload,
    )
    assert filename == "gold.asb"
    assert data == b"ABC123"


def test_parse_multipart_file_rejects_missing_file():
    boundary = "----alphastrategy-test"
    payload = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="note"\r\n\r\n'
        "x"
        f"\r\n--{boundary}--\r\n"
    ).encode("utf-8")
    with pytest.raises(ValueError):
        parse_multipart_file(f"multipart/form-data; boundary={boundary}", payload)


def test_handlers_do_not_import_cgi():
    text = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "alphastrategy"
        / "api"
        / "handlers.py"
    ).read_text(encoding="utf-8")
    assert "import cgi" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_multipart.py -v`

Expected: FAIL (`parse_multipart_file` missing).

- [ ] **Step 3: Write minimal implementation**

Replace `cgi` usage. Parse boundary from `Content-Type`. Split body on `--{boundary}`. For each part, split headers/body on `\r\n\r\n`. Prefer `name="file"`; else first filename part. Filename from `filename="..."`. Strip trailing CRLF before next boundary (the `\r\n` that precedes `--`).

`_extract_upload`:

```python
length = int(handler.headers.get("Content-Length", "0"))
body = handler.rfile.read(length) if length else b""
return parse_multipart_file(handler.headers.get("Content-Type", ""), body)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_multipart.py tests/alphastrategy/test_api.py::test_import_golden_asb_via_api tests/alphastrategy/test_api.py::test_import_bad_zip_returns_400 -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/api/handlers.py tests/alphastrategy/test_multipart.py
git commit -m "fix: parse asb uploads without cgi"
```

---

### Task 6: Mocked e2e for the operator desk fields

**Files:**
- Modify: `tests/alphastrategy/test_e2e_mocked.py`

**Interfaces:**
- Consumes: live server from existing e2e, golden bundle, FakeBroker
- Produces: after import → start → open rebalance, `GET /api/portfolio` has contribution and `GET /api/status` has countdown; after stop, `GET /api/bundles` lists stopped and contribution is unchanged

- [ ] **Step 1: Write the failing test**

Append `test_operator_desk_portfolio_after_rebalance` to `tests/alphastrategy/test_e2e_mocked.py`. Follow `test_v1_done_path` setup through first `tick()`, then `make_server`, then:

```python
conn.request("GET", "/api/portfolio")
portfolio = json.loads(...)
assert portfolio["sleeve_contribution"][bundle_id]
assert portfolio["last_combined"]
conn.request("GET", "/api/status")
status = json.loads(...)
assert status["countdown"]["next_rebalance"] in ("open", "close")
assert "seconds" in status["countdown"]
supervisor.stop_sleeve(bundle_id)
# new connection after stop
conn.request("GET", "/api/bundles")
bundles = json.loads(...)
assert bundle_id in bundles["stopped"]
conn.request("GET", "/api/portfolio")
after_stop = json.loads(...)
assert after_stop["sleeve_contribution"] == portfolio["sleeve_contribution"]
```

Use the same HTTP client pattern as the existing e2e (shutdown in `finally`).

- [ ] **Step 2: Run test to verify it fails or already passes**

If Task 2–3 landed, this may already pass — that is acceptable. If it fails, fix the handler/supervisor, not the test assertion, unless the test assumed the wrong bundle weight shape.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_e2e_mocked.py -v`

- [ ] **Step 3: Fix if needed (minimal)**

Only change production code if the e2e fails. Do not weaken assertions.

- [ ] **Step 4: Run the full alphastrategy suite**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all passed. No real broker.

- [ ] **Step 5: Commit**

```bash
git add tests/alphastrategy/test_e2e_mocked.py
git commit -m "test: e2e operator desk contribution and countdown"
```

---

## Self-review

1. Spec coverage: countdown §3 → Task 1+3+4; last book §4 → Task 2+3+6; stopped §5 → Task 2+3+4; blotter §6 → Task 4; banners/forms/kill §7 → Task 4; multipart §8 → Task 5.
2. No TBD/placeholder steps.
3. Names: `rebalance_countdown`, `RebalanceCountdown`, `last_sleeve_contribution`, `sleeve_contribution` on the wire, `stopped`, `FLATTEN`.
