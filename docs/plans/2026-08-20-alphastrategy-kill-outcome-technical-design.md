# Kill Outcome Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (this cycle explicitly chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return and display whether a sleeve kill isolated or flattened the whole paper account, and keep halt/flatten/kill banners visible on every Quiet cockpit screen.

**Architecture:** Add a `KillOutcome` value object persisted as `snapshot.last_kill`. Supervisor kill methods return it. The control plane and CLI print it. Desk banners move out of the Portfolio screen into always-visible chrome.

**Tech Stack:** Existing Supervisor, stdlib HTTP, static Quiet cockpit, pytest. Tests mock the broker.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-kill-outcome-requirements.md`](../requirements/2026-08-20-alphastrategy-kill-outcome-requirements.md)

## Global Constraints

- Package `alphastrategy`, paper-only walls unchanged.
- Do not grow `src/openstrategy/`.
- Do not change isolation math in `_isolation_ready` / `residual_book`.
- Five `#nav` screens. No `window.confirm`. Account Web kill still requires `FLATTEN`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never place a real order.

## File map

- Modify: `src/alphastrategy/supervisor/state.py` — `KillOutcome`, `last_kill`
- Modify: `src/alphastrategy/supervisor/loop.py` — return outcomes
- Modify: `src/alphastrategy/api/handlers.py` — POST body + status
- Modify: `src/alphastrategy/cli/main.py` — print kill JSON
- Modify: `src/alphastrategy/web/static/index.html` — `#desk-banners`
- Modify: `src/alphastrategy/web/static/app.js` — render kill outcome
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `test_api.py`, `test_cli.py`, `test_web_tokens.py`, `test_e2e_mocked.py`, `test_helptext.py`

---

### Task 1: KillOutcome on snapshot and Supervisor returns

**Files:**
- Modify: `src/alphastrategy/supervisor/state.py`
- Modify: `src/alphastrategy/supervisor/loop.py`
- Test: `tests/alphastrategy/test_halt_flatten.py`

**Interfaces:**
- Produces: `KillOutcome(isolated: bool, flattened: bool, scope: str, reason: str, bundle_id: str | None)` with `to_dict()`
- Produces: `SupervisorSnapshot.last_kill: dict | None`
- Produces: `kill_sleeve` / `kill_account` return `KillOutcome`

- [ ] **Step 1: Write the failing tests**

Append to `tests/alphastrategy/test_halt_flatten.py`:

```python
def test_kill_sleeve_returns_isolated_outcome(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    evaluators = {"asb_a": {"AAPL": 1.0}, "asb_b": {"MSFT": 1.0}}
    supervisor = _make_supervisor(tmp_path, broker, evaluators=evaluators)
    supervisor.start_sleeve("asb_a", 0.15)
    supervisor.start_sleeve("asb_b", 0.15)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    outcome = supervisor.kill_sleeve("asb_a")
    assert outcome.isolated is True
    assert outcome.flattened is False
    assert outcome.scope == "sleeve"
    assert outcome.reason == "isolated"
    assert outcome.bundle_id == "asb_a"
    assert supervisor.snapshot.last_kill["isolated"] is True
    assert supervisor.snapshot.last_kill["reason"] == "isolated"


def test_kill_sleeve_returns_fallback_outcome_when_not_ready(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    outcome = supervisor.kill_sleeve("asb_test")
    assert outcome.isolated is False
    assert outcome.flattened is True
    assert outcome.scope == "account"
    assert outcome.reason == "fallback_not_ready"
    assert supervisor.snapshot.last_kill["flattened"] is True


def test_kill_sleeve_unknown_bundle_does_not_flatten(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    supervisor = _make_supervisor(tmp_path, broker)
    outcome = supervisor.kill_sleeve("missing")
    assert outcome.scope == "none"
    assert outcome.reason == "unknown_sleeve"
    assert outcome.flattened is False
    assert broker.close_all_count == 0
    assert supervisor.snapshot.last_kill["reason"] == "unknown_sleeve"


def test_kill_account_returns_account_outcome(tmp_path: Path):
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    outcome = supervisor.kill_account()
    assert outcome.isolated is False
    assert outcome.flattened is True
    assert outcome.scope == "account"
    assert outcome.reason == "account"
    assert outcome.bundle_id is None
```

- [ ] **Step 2: Run to verify FAIL**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_kill_sleeve_returns_isolated_outcome tests/alphastrategy/test_halt_flatten.py::test_kill_sleeve_unknown_bundle_does_not_flatten -q`

Expected: FAIL (`None` has no `isolated` / or AttributeError)

- [ ] **Step 3: Minimal implementation**

In `src/alphastrategy/supervisor/state.py` add before `SupervisorSnapshot`:

```python
@dataclass(frozen=True)
class KillOutcome:
    isolated: bool
    flattened: bool
    scope: str
    reason: str
    bundle_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "isolated": self.isolated,
            "flattened": self.flattened,
            "scope": self.scope,
            "reason": self.reason,
            "bundle_id": self.bundle_id,
        }


def _kill_from_payload(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    return {
        "isolated": bool(raw.get("isolated")),
        "flattened": bool(raw.get("flattened")),
        "scope": str(raw.get("scope") or "none"),
        "reason": str(raw.get("reason") or ""),
        "bundle_id": (None if raw.get("bundle_id") in (None, "") else str(raw.get("bundle_id"))),
    }
```

Add field `last_kill: dict[str, Any] | None = None` on `SupervisorSnapshot`.

In `from_dict`, pass `last_kill=_kill_from_payload(payload.get("last_kill"))`.

In `loop.py` import `KillOutcome`. Add helper on `Supervisor`:

```python
    def _record_kill(self, outcome: KillOutcome) -> KillOutcome:
        self._snapshot.last_kill = outcome.to_dict()
        self._persist()
        return outcome
```

Change `kill_sleeve`:

```python
    def kill_sleeve(self, bundle_id: str) -> KillOutcome:
        with self._lock:
            if bundle_id not in self._snapshot.sleeves:
                return self._record_kill(
                    KillOutcome(
                        isolated=False,
                        flattened=False,
                        scope="none",
                        reason="unknown_sleeve",
                        bundle_id=bundle_id,
                    )
                )
            self._snapshot.sleeves[bundle_id] = 0.0
            if bundle_id not in self._snapshot.stopped:
                self._snapshot.stopped.append(bundle_id)
            if self._isolation_ready(bundle_id):
                try:
                    self._isolate_sleeve(bundle_id)
                    self._audit("kill", bundle_id=bundle_id, isolated=True)
                    return self._record_kill(
                        KillOutcome(
                            isolated=True,
                            flattened=False,
                            scope="sleeve",
                            reason="isolated",
                            bundle_id=bundle_id,
                        )
                    )
                except Exception:
                    self._flatten_account()
                    self._audit("kill", bundle_id=bundle_id, isolated=False)
                    return self._record_kill(
                        KillOutcome(
                            isolated=False,
                            flattened=True,
                            scope="account",
                            reason="fallback_error",
                            bundle_id=bundle_id,
                        )
                    )
            self._flatten_account()
            self._audit("kill", bundle_id=bundle_id, isolated=False)
            return self._record_kill(
                KillOutcome(
                    isolated=False,
                    flattened=True,
                    scope="account",
                    reason="fallback_not_ready",
                    bundle_id=bundle_id,
                )
            )
```

Change `kill_account`:

```python
    def kill_account(self) -> KillOutcome:
        with self._lock:
            self._flatten_account()
            self._audit("kill", scope="account")
            return self._record_kill(
                KillOutcome(
                    isolated=False,
                    flattened=True,
                    scope="account",
                    reason="account",
                    bundle_id=None,
                )
            )
```

`_record_kill` already persists; `kill_sleeve` previously persisted after audit — `_record_kill` replaces that final persist. Keep the sleeve mutation + audit before `_record_kill`. Do not double-persist in a way that drops fields: `_flatten_account` also persists; `_record_kill` after that is required so `last_kill` is on disk.

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/supervisor/state.py src/alphastrategy/supervisor/loop.py tests/alphastrategy/test_halt_flatten.py
git commit -m "feat: return and persist sleeve-kill isolated vs flatten outcome"
```

---

### Task 2: API kill body and status.last_kill

**Files:**
- Modify: `src/alphastrategy/api/handlers.py`
- Test: `tests/alphastrategy/test_api.py`

**Interfaces:**
- Consumes: `KillOutcome.to_dict()`
- Produces: POST `/api/paper/kill` `{ok: true, ...outcome}`; GET `/api/status` `last_kill`

- [ ] **Step 1: Write the failing tests**

Append to `tests/alphastrategy/test_api.py`:

```python
def test_api_kill_sleeve_returns_isolated_payload(api_stack):
    client, _home, supervisor, broker = api_stack
    supervisor.start_sleeve("asb_x", 0.15)
    supervisor.start_sleeve("asb_y", 0.15)
    broker._is_open = True
    broker._now = datetime(2024, 1, 31, 14, 33)
    supervisor.tick()
    response = client.post("/api/paper/kill", json={"bundle_id": "asb_x"})
    assert response.status == 200
    body = response.json()
    assert body["ok"] is True
    assert body["isolated"] is True
    assert body["flattened"] is False
    assert body["reason"] == "isolated"
    status = client.get("/api/status").json()
    assert status["last_kill"]["reason"] == "isolated"
    assert status["last_kill"]["bundle_id"] == "asb_x"


def test_api_kill_account_returns_account_payload(api_stack):
    client, _home, supervisor, _broker = api_stack
    response = client.post("/api/paper/kill", json={})
    assert response.status == 200
    body = response.json()
    assert body["isolated"] is False
    assert body["flattened"] is True
    assert body["reason"] == "account"
    status = client.get("/api/status").json()
    assert status["last_kill"]["reason"] == "account"
```

- [ ] **Step 2: Run to verify FAIL**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_api_kill_sleeve_returns_isolated_payload -q`

Expected: FAIL missing `isolated` key

- [ ] **Step 3: Implement**

In `handle_get_status` payload add:

```python
            "last_kill": snapshot.last_kill,
```

In `handle_post_paper_kill`:

```python
        if bundle_id:
            outcome = supervisor.kill_sleeve(str(bundle_id))
        else:
            outcome = supervisor.kill_account()
        _json_response(handler, 200, {"ok": True, **outcome.to_dict()})
```

- [ ] **Step 4: Run**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_api_kill_sleeve_returns_isolated_payload tests/alphastrategy/test_api.py::test_api_kill_account_returns_account_payload tests/alphastrategy/test_api.py::test_api_kill_sleeve_isolates tests/alphastrategy/test_api.py::test_status_returns_state_clock_and_halt -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/api/handlers.py tests/alphastrategy/test_api.py
git commit -m "feat: expose kill outcome on POST /api/paper/kill and status"
```

---

### Task 3: CLI prints kill JSON

**Files:**
- Modify: `src/alphastrategy/cli/main.py`
- Test: `tests/alphastrategy/test_cli.py`

**Interfaces:**
- Consumes: Task 2 JSON / Task 1 `to_dict()`
- Produces: stdout one JSON object

- [ ] **Step 1: Write the failing test**

Append to `tests/alphastrategy/test_cli.py`:

```python
def test_paper_kill_prints_isolated_json(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    _create_imported_bundle(cli_home, "asb_test")
    home = AlphaStrategyHome.root if False else AlphaStrategyHome.from_env()
    broker = FakeBroker()
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        rc = main(
            [
                "paper",
                "kill",
                "--bundle",
                "asb_test",
                "--port",
                str(server.server_port),
            ]
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["reason"] == "fallback_not_ready"
    assert payload["flattened"] is True
    assert payload["isolated"] is False
```

(`_create_imported_bundle` already exists. No last book → fallback_not_ready. Use `AlphaStrategyHome.from_env()` because `cli_home` fixture sets `ALPHASTRATEGY_HOME`.)

- [ ] **Step 2: Run to verify FAIL**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_cli.py::test_paper_kill_prints_isolated_json -q`

Expected: FAIL empty stdout / JSON decode error

- [ ] **Step 3: Implement**

In `cli/main.py`:

```python
def _control_json(response: tuple[int, dict[str, Any]]) -> int:
    status, payload = response
    if 200 <= status < 300:
        print(json.dumps(payload, separators=(",", ":")))
        return 0
    print(f"error: {payload.get('error', f'HTTP {status}')}", file=sys.stderr)
    return 1
```

In `_cmd_paper_kill`, on control-plane hit: `return _control_json(response)`. Offline:

```python
    if bundle_id:
        outcome = supervisor.kill_sleeve(bundle_id)
    else:
        outcome = supervisor.kill_account()
    print(json.dumps(outcome.to_dict(), separators=(",", ":")))
    return 0
```

Import `KillOutcome` not required if using `outcome.to_dict()`.

- [ ] **Step 4: Run**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_cli.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/cli/main.py tests/alphastrategy/test_cli.py
git commit -m "feat: print paper kill outcome JSON on the CLI"
```

---

### Task 4: Always-visible desk banners + kill outcome copy

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`
- Modify: `src/alphastrategy/web/static/app.js`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_api.py`

**Interfaces:**
- Consumes: `status.last_kill`
- Produces: `#desk-banners` sibling of screens; `#kill-outcome-banner`

- [ ] **Step 1: Write the failing tests**

Append to `test_web_tokens.py`:

```python
def test_html_desk_banners_outside_portfolio(html_text: str) -> None:
    desk_at = html_text.find('id="desk-banners"')
    portfolio_at = html_text.find('id="screen-portfolio"')
    assert desk_at != -1
    assert 0 <= desk_at < portfolio_at
    for banner_id in (
        "halt-banner",
        "flatten-banner",
        "deviation-banner",
        "control-plane-banner",
        "kill-outcome-banner",
    ):
        assert html_text.find(f'id="{banner_id}"') < portfolio_at
        assert html_text.count(f'id="{banner_id}"') == 1


def test_js_renders_kill_outcome_from_last_kill(js_text: str) -> None:
    assert "kill-outcome-banner" in js_text
    assert "last_kill" in js_text
    assert "SLEEVE KILL: isolated residual" in js_text
    assert "could not isolate" in js_text
    assert "unknown sleeve" in js_text
```

- [ ] **Step 2: Run to verify FAIL**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_desk_banners_outside_portfolio -q`

Expected: FAIL missing `desk-banners`

- [ ] **Step 3: Implement HTML + JS**

In `index.html`, inside `<main>`, **before** `#screen-portfolio`, insert:

```html
      <div id="desk-banners">
        <div id="halt-banner" class="banner halt hidden" role="alert"></div>
        <div id="flatten-banner" class="banner fail hidden" role="alert"></div>
        <div id="deviation-banner" class="banner fail hidden" role="alert"></div>
        <div id="control-plane-banner" class="banner fail hidden" role="alert"></div>
        <div id="kill-outcome-banner" class="banner halt hidden" role="alert"></div>
      </div>
```

Remove the four banner divs from `#screen-portfolio`.

In `app.js` `renderBanners`, after flatten/deviation handling, add:

```javascript
    const killEl = document.getElementById("kill-outcome-banner");
    const lastKill = state.status && state.status.last_kill;
    const reason = lastKill && lastKill.reason;
    if (reason === "isolated") {
      killEl.className = "banner halt";
      killEl.textContent =
        "SLEEVE KILL: isolated residual for " +
        (lastKill.bundle_id || "sleeve") +
        " — other sleeves still live";
    } else if (reason === "fallback_not_ready" || reason === "fallback_error") {
      killEl.className = "banner fail";
      killEl.textContent =
        "SLEEVE KILL: could not isolate — whole paper account flattened";
    } else if (reason === "unknown_sleeve") {
      killEl.className = "banner halt";
      killEl.textContent =
        "SLEEVE KILL: unknown sleeve " + (lastKill.bundle_id || "");
    } else {
      killEl.className = "banner halt hidden";
      killEl.textContent = "";
    }
```

Keep existing halt/flatten/deviation logic. `renderBanners` is called from `renderPortfolio`; also call `renderBanners()` at the end of successful `refresh()` so banners update even if Portfolio render is skipped? `renderPortfolio` always runs today. Keep calling it from `renderPortfolio` and also from the control-plane error path (already sets control-plane banner). Fine.

- [ ] **Step 4: Run**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_api.py::test_get_root_includes_help_control -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/web/static/index.html src/alphastrategy/web/static/app.js tests/alphastrategy/test_web_tokens.py
git commit -m "feat: always-visible desk banners and sleeve-kill outcome copy"
```

---

### Task 5: Help, README, e2e

**Files:**
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`
- Modify: `tests/alphastrategy/test_e2e_mocked.py`
- Modify: `tests/alphastrategy/test_helptext.py` only if required phrases still pass (they should)

- [ ] **Step 1: Write e2e test**

Append to `test_e2e_mocked.py`:

```python
def test_e2e_isolated_kill_reports_outcome(tmp_path: Path) -> None:
    home = AlphaStrategyHome(root=tmp_path)
    home.root.mkdir(parents=True, exist_ok=True)
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    _setup_broker_bars(broker)
    bundle_id = import_asb(GOLDEN_ASB, home)
    supervisor = _make_supervisor(home, broker)
    supervisor.start_sleeve(bundle_id, 0.4)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        payload = json.dumps({"bundle_id": bundle_id}).encode("utf-8")
        conn.request(
            "POST",
            "/api/paper/kill",
            body=payload,
            headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
        )
        kill_body = json.loads(conn.getresponse().read().decode("utf-8"))
        assert kill_body["isolated"] is True
        conn.request("GET", "/api/status")
        status = json.loads(conn.getresponse().read().decode("utf-8"))
        assert status["last_kill"]["reason"] == "isolated"
        conn.request("GET", "/")
        html = conn.getresponse().read().decode("utf-8")
        assert 'id="desk-banners"' in html
        assert 'id="kill-outcome-banner"' in html
    finally:
        server.shutdown()
        thread.join(timeout=2)
```

Check whether golden.asb is a single-name universe — isolation with one sleeve still works (residual empty). Isolated true, account not STOPPED.

If golden is only one sleeve, isolation still returns isolated=True and does not close_all. Good.

- [ ] **Step 2: Run e2e (may FAIL if HTML not done — Task 4 first)**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_e2e_mocked.py::test_e2e_isolated_kill_reports_outcome -q`

Expected: PASS after Task 4

- [ ] **Step 3: Help + README**

In `helptext.py` halt_flatten body, append: ` Sleeve kill reports whether isolation succeeded or the whole paper account was flattened. Desk banners stay visible on every screen.`

In README Operator, add: `- Sleeve kill outcome is JSON on the CLI and a desk banner (isolated vs whole-account flatten). Halt/FLAT banners stay visible on every screen, not only Portfolio.`

- [ ] **Step 4: Full suite**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/helptext.py README.md tests/alphastrategy/test_e2e_mocked.py
git commit -m "docs: sleeve-kill outcome in help; e2e last_kill"
```

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| KillOutcome + last_kill persist | 1 |
| API POST + status | 2 |
| CLI JSON | 3 |
| Desk banners outside Portfolio + copy | 4 |
| Help/README + e2e | 5 |
| Isolation math unchanged | Global |
