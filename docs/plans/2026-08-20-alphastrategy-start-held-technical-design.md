# Start Paper While Halted Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record paper allocation while HALTED without leaving halt or catching up, and say so at Start paper (Web), on `POST /api/paper/start` (`held`), and on CLI stderr.

**Architecture:** `start_sleeve` returns whether state is still `HALTED` after the existing STOPPED restart path. The API forwards that bool. Run paints a persistent `#run-start-hint` from `status` (halt warn / flatten fail / idle muted) and a stable `#run-stop-hint`. No 409. No stdout JSON on `paper start`.

**Tech Stack:** Supervisor, local HTTP API, Quiet cockpit JS parts, argparse CLI, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-start-held-requirements.md`](../requirements/2026-08-20-alphastrategy-start-held-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Do not retry leftover orders. Do not un-consume `last_rebalance_event`. Do not change halt/flatten/isolate recovery actions.
- Resume does not catch up. Start paper after flatten still leaves `STOPPED` via the existing idle transition.
- Keep tutorial substring `Next rebalance`. Keep Clock Next `held ·` / `flat ·`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.
- Each JS part ≤ 400 lines. No on-disk `static/app.js`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/cli/main.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/js/paint-run.js`, `src/alphastrategy/web/static/js/boot.js`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_e2e_mocked.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_halt_flatten.py`
- Modify: `tests/alphastrategy/test_api.py`
- Modify: `tests/alphastrategy/test_cli.py`
- Modify: `tests/alphastrategy/test_web_tokens.py`
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_e2e_mocked.py`

- [ ] **Step 1: Write the failing tests**

In `tests/alphastrategy/test_halt_flatten.py` after `test_start_sleeve_after_flatten_leaves_stopped_without_catchup` add:

```python
def test_start_sleeve_while_halted_stays_halted_without_catchup(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=True,
        next_open=open_time,
        next_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor = _make_supervisor(tmp_path, broker)
    assert supervisor.start_sleeve("asb_test", 0.15) is False
    supervisor._halt("stale bars")
    assert supervisor.state == SupervisorState.HALTED
    orders_before = list(broker.orders)
    held = supervisor.start_sleeve("asb_test", 0.4)
    assert held is True
    assert supervisor.state == SupervisorState.HALTED
    assert supervisor.snapshot.sleeves["asb_test"] == 0.4
    supervisor.tick()
    assert supervisor.state == SupervisorState.HALTED
    assert broker.orders == orders_before
```

In `tests/alphastrategy/test_api.py` after `test_start_replaces_existing_sleeve_allocation` add (import `SupervisorState` if missing):

```python
def test_start_while_halted_returns_held(api_stack):
    client, _home, supervisor, _broker = api_stack
    first = client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.15})
    assert first.status == 200
    assert first.json()["ok"] is True
    assert first.json()["held"] is False
    supervisor._halt("stale bars")
    second = client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.2})
    assert second.status == 200
    body = second.json()
    assert body["ok"] is True
    assert body["held"] is True
    assert supervisor.state == SupervisorState.HALTED
    assert supervisor.snapshot.sleeves["asb_x"] == 0.2
```

In `tests/alphastrategy/test_cli.py` after `test_paper_stop_help_mentions_next_rebalance` add:

```python
def test_paper_start_help_mentions_halted_waits(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["paper", "start", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "halt" in out
    assert "resume" in out


def test_paper_start_while_halted_prints_held(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    from alphastrategy.home import AlphaStrategyHome
    from alphastrategy.live.alpaca import AlpacaBroker
    from alphastrategy.risk.policy import AccountPolicy
    from alphastrategy.supervisor.loop import Supervisor
    from alphastrategy.supervisor.state import SupervisorState

    _create_imported_bundle(cli_home)
    home = AlphaStrategyHome.from_env()
    supervisor = Supervisor(
        home=home,
        broker=AlpacaBroker(key="PK_test", secret="SK_test", paper=True),
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.start_sleeve("asb_test", 0.25)
    supervisor._halt("stale bars")
    assert supervisor.state == SupervisorState.HALTED
    rc = main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.3"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "held:" in err.lower()
    assert "resume" in err.lower()
    assert "catch up" in err.lower()
```

Look at nearby CLI tests that construct `Supervisor` + `AlpacaBroker` and copy that constructor (do not invent a different broker). If `AlpacaBroker` is patched, constructing it is fine.

In `tests/alphastrategy/test_web_tokens.py` add:

```python
def test_html_run_start_and_stop_hints(html_text: str) -> None:
    run = html_text[html_text.find('id="screen-run"') : html_text.find('id="screen-activity"')]
    promote = run[run.find('id="run-promote"') : run.find('id="run-book"')]
    book = run[run.find('id="run-book"') : run.find('id="run-recover"')]
    assert 'id="run-start-hint"' in promote
    assert 'id="start-form"' in promote
    assert promote.find('id="start-form"') < promote.find('id="run-start-hint"')
    assert promote.find('id="run-start-hint"') < promote.find('id="run-error"')
    assert "Start paper is a second explicit action" in promote
    assert 'id="run-stop-hint"' in book
    assert "Stop zeros that sleeve on the next legal rebalance" in book
    assert 'id="run-stop-hint"' not in promote
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_paints_run_start_hint(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRunStartHint") : js_text.find("function renderRunStopHint")
    ]
    assert "run-start-hint" in paint
    assert "Start paper while halted waits for resume. Resume does not catch up." in paint
    assert "Start paper after flatten starts the session loop again and does not catch up." in paint
    assert "Start paper is a second explicit action. Import is not permission to trade." in paint
    assert 'className = "warn"' in paint
    assert 'className = "fail"' in paint
    assert "innerHTML" not in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
    assert "renderRunStartHint();" in js_text
    refresh = js_text[js_text.find("async function refresh") : js_text.find("async function stopSleeve")]
    assert "renderRunStartHint" in refresh
    assert "renderRunStopHint" in refresh
    assert "runFormIsDirty" in refresh


def test_js_paints_run_stop_hint(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRunStopHint") : js_text.find("function renderRunRecover")
    ]
    assert "run-stop-hint" in paint
    assert "Stop zeros that sleeve on the next legal rebalance and does not flatten now." in paint
    assert "innerHTML" not in paint


def test_css_run_start_hint_tokens(css_text: str) -> None:
    warn = re.search(r"#run-start-hint\.warn\s*\{[^}]*\}", css_text)
    fail = re.search(r"#run-start-hint\.fail\s*\{[^}]*\}", css_text)
    assert warn is not None and "#f59e0b" in warn.group(0).lower()
    assert fail is not None and "#ef4444" in fail.group(0).lower()
```

`REQUIRED_PHRASES` in `tests/alphastrategy/test_helptext.py` add:

```python
    "Start paper while halted waits for resume",
```

In `tests/alphastrategy/test_e2e_mocked.py`, after the halted tick asserts and before `make_server`, add:

```python
    orders_before_held_start = list(broker.orders)
    held = halted_supervisor.start_sleeve(bundle_id, 0.5)
    assert held is True
    assert halted_supervisor.state == SupervisorState.HALTED
    halted_supervisor.tick()
    assert halted_supervisor.state == SupervisorState.HALTED
    assert broker.orders == orders_before_held_start
    assert broker.close_all_count == close_all_before_halt
```

Place that **after** `close_all_before_halt` is assigned and the first halted `tick()` has run.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_while_halted_stays_halted_without_catchup tests/alphastrategy/test_api.py::test_start_while_halted_returns_held tests/alphastrategy/test_cli.py::test_paper_start_help_mentions_halted_waits tests/alphastrategy/test_cli.py::test_paper_start_while_halted_prints_held tests/alphastrategy/test_web_tokens.py::test_html_run_start_and_stop_hints tests/alphastrategy/test_web_tokens.py::test_js_paints_run_start_hint tests/alphastrategy/test_web_tokens.py::test_js_paints_run_stop_hint tests/alphastrategy/test_web_tokens.py::test_css_run_start_hint_tokens tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_e2e_mocked.py::test_import_start_rebalance_flatten_halt_kill_mocked -q
```

Expected: FAIL because `start_sleeve` returns `None`, API body has no `held`, HTML ids missing, phrases missing.

- [ ] **Step 3: Commit failing tests and requirements**

```bash
git add docs/requirements/2026-08-20-alphastrategy-start-held-requirements.md docs/plans/2026-08-20-alphastrategy-start-held-technical-design.md tests/alphastrategy/test_halt_flatten.py tests/alphastrategy/test_api.py tests/alphastrategy/test_cli.py tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_helptext.py tests/alphastrategy/test_e2e_mocked.py
git commit -m "test: start paper while halted is held"
```

---

### Task 2: Engine, API, CLI

**Files:**
- Modify: `src/alphastrategy/supervisor/loop.py` (`start_sleeve`)
- Modify: `src/alphastrategy/api/handlers.py` (`handle_post_paper_start`)
- Modify: `src/alphastrategy/cli/main.py`

**Interfaces:**
- Consumes: existing `start_sleeve` rules
- Produces: `start_sleeve(...) -> bool`; API `{ok: true, held: bool}`

- [ ] **Step 1: Return held from start_sleeve**

Change signature to `-> bool`. After persist, `return self._snapshot.state == SupervisorState.HALTED`. Do not add a HALTED branch that changes state.

- [ ] **Step 2: API body**

```python
        held = supervisor.start_sleeve(bundle_id, allocation)
        _json_response(handler, 200, {"ok": True, "held": held})
```

- [ ] **Step 3: CLI**

`paper start` parser help/description include halted waits for resume.

Shared line:

```python
_HELD_START = "held: start paper while halted waits for resume. Resume does not catch up."
```

`_cmd_paper_start`: on HTTP 2xx, if `payload.get("held")` print `_HELD_START` to stderr. Offline: `held = supervisor.start_sleeve(...)`; if held, same print. Return 0. Do not print JSON to stdout.

- [ ] **Step 4: Run the engine/API/CLI tests**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_while_halted_stays_halted_without_catchup tests/alphastrategy/test_api.py::test_start_while_halted_returns_held tests/alphastrategy/test_cli.py::test_paper_start_help_mentions_halted_waits tests/alphastrategy/test_cli.py::test_paper_start_while_halted_prints_held tests/alphastrategy/test_cli.py::test_status_prints_json -q
```

Expected: PASS. `test_status_prints_json` must still parse a single JSON object from stdout.

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/supervisor/loop.py src/alphastrategy/api/handlers.py src/alphastrategy/cli/main.py
git commit -m "feat: start_sleeve returns held while halted"
```

---

### Task 3: Run paint, help, README

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`, `styles.css`, `js/paint-run.js`, `js/boot.js`
- Modify: `src/alphastrategy/helptext.py`, `README.md`

- [ ] **Step 1: HTML**

Inside `#run-promote` `.panel`, after `</form>` and before `#run-error`:

```html
          <p id="run-start-hint" class="muted">Start paper is a second explicit action. Import is not permission to trade.</p>
```

Inside `#run-book`, after the `metrics-4` block and before `#run-sleeve-error`:

```html
        <p id="run-stop-hint" class="muted">Stop zeros that sleeve on the next legal rebalance and does not flatten now.</p>
```

- [ ] **Step 2: CSS** (after `#run-halt-reason.warn`)

```css
#run-start-hint.warn {
  color: #f59e0b;
}

#run-start-hint.fail {
  color: #ef4444;
}
```

- [ ] **Step 3: JS**

In `paint-run.js` **before** `function renderRunRecover`:

```javascript
  function renderRunStartHint() {
    const el = document.getElementById("run-start-hint");
    if (!el) return;
    const halted =
      (state.status && state.status.state === "halted") ||
      Boolean(state.status && state.status.halted);
    const flattened =
      Boolean(state.status && state.status.flattened) ||
      (state.status &&
        (state.status.state === "flattening" || state.status.state === "stopped"));
    if (halted) {
      el.className = "warn";
      el.textContent =
        "Start paper while halted waits for resume. Resume does not catch up.";
      return;
    }
    if (flattened) {
      el.className = "fail";
      el.textContent =
        "Start paper after flatten starts the session loop again and does not catch up.";
      return;
    }
    el.className = "muted";
    el.textContent =
      "Start paper is a second explicit action. Import is not permission to trade.";
  }

  function renderRunStopHint() {
    const el = document.getElementById("run-stop-hint");
    if (!el) return;
    el.className = "muted";
    el.textContent =
      "Stop zeros that sleeve on the next legal rebalance and does not flatten now.";
  }
```

In `boot.js` `refresh()`, after `renderRunRecover();` add:

```javascript
      renderRunStartHint();
      renderRunStopHint();
```

Do not gate those two on `runFormIsDirty()`. Do not add `"Gross cap"` to JS. Keep a single `const reason` in `renderBanners`.

- [ ] **Step 4: Help / README**

`how_run` body, after `Start paper is a second explicit action. `:

`Start paper while halted waits for resume. Resume does not catch up. `

`task_start` body, after the flatten restart sentence, same Start-while-halted sentence.

README Operator halt bullet: `Start paper while halted waits for resume. Resume does not catch up.`

- [ ] **Step 5: Run paint/help tests**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_run_start_and_stop_hints tests/alphastrategy/test_web_tokens.py::test_js_paints_run_start_hint tests/alphastrategy/test_web_tokens.py::test_js_paints_run_stop_hint tests/alphastrategy/test_web_tokens.py::test_css_run_start_hint_tokens tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_html_has_no_live_toggle_label tests/alphastrategy/test_cockpit_js_assembled_from_parts -q
```

(Use the real collected name for the cockpit-parts test if different.) Expected: PASS. `paint-run.js` still ≤ 400 lines.

- [ ] **Step 6: Commit**

```bash
git add src/alphastrategy/web/static/index.html src/alphastrategy/web/static/styles.css src/alphastrategy/web/static/js/paint-run.js src/alphastrategy/web/static/js/boot.js src/alphastrategy/helptext.py README.md
git commit -m "feat: paint Start paper held while halted"
```

---

### Task 4: Full suite

- [ ] **Step 1: Run**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

Expected: all passed. No real broker.

- [ ] **Step 2: Commit any fixes**

If green and already committed, skip.

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| `start_sleeve` stays HALTED, returns held, no catch-up | 1–2 |
| API `{ok, held}` | 1–2 |
| CLI help + stderr, no stdout JSON | 1–2 |
| `#run-start-hint` / `#run-stop-hint` paint | 3 |
| Help / README phrase | 3 |
| e2e start while halted | 1, 4 |

No placeholders. No 409-on-halt. No Clock Next rewrite.
