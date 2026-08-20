# Supervisor Heartbeat Pulse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stamp a Supervisor liveness beat on every `tick()`, expose pulse on status/CLI, and show LIVE/STALE/DEAD on the Quiet cockpit header plus an honest Activity empty state.

**Architecture:** `supervisor/heartbeat.py` is the single source of interval and pulse bands. `tick()` writes `last_heartbeat_at` and persists even on halt/flatten/stop. Handlers and CLI call `describe()`. The cockpit paints `#desk-pulse`. No audit rows. No WebSockets.

**Tech Stack:** Python 3.9+, stdlib HTTP, static HTML/CSS/JS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-heartbeat-pulse-requirements.md`](../requirements/2026-08-20-alphastrategy-heartbeat-pulse-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets.
- Heartbeat does not place orders. Do not emit audit events for beats.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Create: `src/alphastrategy/supervisor/heartbeat.py`
- Create: `tests/alphastrategy/test_heartbeat.py`
- Modify: `src/alphastrategy/supervisor/state.py`, `loop.py`
- Modify: `src/alphastrategy/api/app.py`, `handlers.py`, `cli/main.py`
- Modify: `web/static/index.html`, `styles.css`, `app.js`
- Modify: `helptext.py`, `README.md`
- Test: `test_api.py`, `test_cli.py`, `test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`, `test_halt_flatten.py` (halted tick still stamps)

---

### Task 1: Pulse helper + snapshot field + tick stamp

**Files:** `heartbeat.py`, `state.py`, `loop.py`, `api/app.py`, `test_heartbeat.py`, halt/flatten tick assertion

- [ ] **Step 1: Failing tests** — create `tests/alphastrategy/test_heartbeat.py`

```python
from datetime import datetime, timedelta, timezone

from alphastrategy.supervisor.heartbeat import (
    INTERVAL_SEC,
    describe,
    pulse_from_age,
)


def test_pulse_bands() -> None:
    assert pulse_from_age(None) == "missing"
    assert pulse_from_age(0) == "live"
    assert pulse_from_age(45) == "live"
    assert pulse_from_age(46) == "stale"
    assert pulse_from_age(90) == "stale"
    assert pulse_from_age(91) == "dead"


def test_describe_missing_and_live() -> None:
    missing = describe(None)
    assert missing["pulse"] == "missing"
    assert missing["at"] is None
    assert missing["age_seconds"] is None
    assert missing["interval_seconds"] == INTERVAL_SEC == 20
    now = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
    at = (now - timedelta(seconds=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = describe(at, now=now)
    assert body["pulse"] == "live"
    assert body["age_seconds"] == 3
    assert body["at"] == at
```

In `test_halt_flatten.py` (use existing `_make_supervisor` / FakeBroker):

```python
def test_tick_stamps_heartbeat_when_halted(tmp_path: Path) -> None:
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    supervisor._snapshot.state = SupervisorState.HALTED
    supervisor._persist()
    supervisor.tick()
    assert supervisor.snapshot.last_heartbeat_at
    on_disk = load_state(supervisor._home.state_path())
    assert on_disk.last_heartbeat_at == supervisor.snapshot.last_heartbeat_at
```

Need `load_state` import if missing.

- [ ] **Step 2:** Run tests — FAIL (no module / no field).

- [ ] **Step 3: Implementation**

`heartbeat.py`: `INTERVAL_SEC = 20`, `LIVE_MAX_SEC = 45`, `STALE_MAX_SEC = 90`, `pulse_from_age`, `describe`. Parse ISO with `Z` → `+00:00`.

`SupervisorSnapshot.last_heartbeat_at: str | None = None` in dataclass and `from_dict`.

`tick()` immediately after `reload_from_disk()`:

```python
self._snapshot.last_heartbeat_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
```

On `STOPPED` / `FLATTENING` / `HALTED` early return: `_persist()` then `return`.

`app.py`: `from alphastrategy.supervisor.heartbeat import INTERVAL_SEC as HEARTBEAT_INTERVAL_SEC` and delete the literal `HEARTBEAT_INTERVAL_SEC = 20`.

- [ ] **Step 4:** Those tests PASS.

---

### Task 2: Status + CLI

**Files:** `handlers.py`, `cli/main.py`, `test_api.py`, `test_cli.py`

- [ ] **Step 1: Failing tests**

```python
def test_status_heartbeat_missing_before_tick(api_client: ApiClient) -> None:
    body = api_client.get("/api/status").json()
    assert body["heartbeat"]["pulse"] == "missing"
    assert body["heartbeat"]["interval_seconds"] == 20


def test_status_heartbeat_live_after_tick(api_stack) -> None:
    client, _home, supervisor, _broker = api_stack
    supervisor.tick()
    body = client.get("/api/status").json()
    assert body["heartbeat"]["pulse"] == "live"
    assert body["heartbeat"]["at"]
```

CLI `test_status_prints_json`: `assert "heartbeat" in payload`.

- [ ] **Step 2:** FAIL.

- [ ] **Step 3:** `handle_get_status` and offline `_cmd_status` add `"heartbeat": describe(snapshot.last_heartbeat_at)`.

- [ ] **Step 4:** PASS.

---

### Task 3: Header pulse + Activity empty

**Files:** `index.html`, `styles.css`, `app.js`, `test_web_tokens.py`, `test_e2e_mocked.py`

- [ ] **Step 1: Failing tests**

```python
def test_html_desk_pulse_and_activity_heartbeat(html_text: str) -> None:
    assert 'id="desk-pulse"' in html_text
    assert 'id="desk-pulse-label"' in html_text
    assert 'id="activity-heartbeat"' in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_desk_pulse_and_activity_empty(js_text: str) -> None:
    assert "function renderDeskPulse" in js_text
    assert "Heartbeat is running. No audit events yet. Rebalances fire at open+3m and close−12m." in js_text
    assert "No audit events yet. Supervisor beat is not live." in js_text
    assert "window.confirm" not in js_text
```

CSS: `.desk-pulse`, `.pulse-dot`, `prefers-reduced-motion`.

e2e GET `/`: `id="desk-pulse"`.

- [ ] **Step 2:** FAIL.

- [ ] **Step 3:** HTML mounts. CSS pulse-dot colors via `.desk-pulse.live|.stale|.dead|.missing`. JS `renderDeskPulse` maps pulse → LIVE/STALE/DEAD/NO BEAT; `renderActivity` writes `#activity-heartbeat` and the two empty strings. Call `renderDeskPulse` from `refresh` after status is stored (and from `renderBanners` or `refresh` so every screen sees it — header is outside screens).

- [ ] **Step 4:** PASS.

---

### Task 4: Help / README

Cockpit + execution: header LIVE is the Supervisor beat, not RTH Session OPEN. Activity empty names open+3m and close−12m.

`REQUIRED_PHRASES` add `"Supervisor beat"` or `"LIVE"`.

Full suite green.

## Spec coverage

| Requirement | Task |
| --- | --- |
| stamp every tick including halt/stop | 1 |
| describe / pulse bands / INTERVAL import | 1 |
| status + CLI | 2 |
| header + Activity | 3 |
| Help / README | 4 |
| no audit spam / no order change | no edits to `orders.py` |
