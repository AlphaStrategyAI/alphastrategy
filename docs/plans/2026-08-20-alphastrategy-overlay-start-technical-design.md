# Overlay-on-Start Live Book Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When Start paper makes a tighter idle sleeve overlay spoken, flatten now if the live book already breaches it, instead of waiting for the next legal rebalance.

**Architecture:** After `start_sleeve` persist, call `_enforce_live_book()` on the same lock. Overlays still enter `_rebalance_policy` only when allocation > 0. PUT overlay while allocated already enforces (lock). Start API returns `flattened`. CLI stderr names flatten. Risk overlay band gets a persistent warn hint.

**Tech Stack:** Supervisor, `check_book`, local HTTP API, Quiet cockpit HTML/CSS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-overlay-start-requirements.md`](../requirements/2026-08-20-alphastrategy-overlay-start-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten and does not place orders.
- Do not retry leftover orders. Do not change halt/flatten/isolate crash recovery.
- Do not 409 `POST /api/paper/start`. CLI `paper start` prints no JSON on stdout.
- Live-book tests use **15** shares × $100 / $10k = 0.15 weight (not 40).
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/cli/main.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

In `tests/alphastrategy/test_halt_flatten.py` after `test_set_policy_ok_when_live_book_inside_cap` add:

```python
def test_start_sleeve_flattens_when_idle_overlay_breaches_live_book(tmp_path: Path):
    broker = FakeBroker(equity=10_000.0)
    broker.positions = {"AAPL": 15.0}
    supervisor = _make_supervisor(tmp_path, broker)
    home = AlphaStrategyHome(root=tmp_path)
    bundle_dir = home.bundle_dir("asb_test")
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")
    home.runtime_path().write_text(
        yaml.safe_dump({"sleeve_overlays": {"asb_test": {"max_name_weight": 0.05}}}),
        encoding="utf-8",
    )
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    held = supervisor.start_sleeve("asb_test", 0.25)
    assert held is False
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1
    assert supervisor.snapshot.last_kill is not None
    assert supervisor.snapshot.last_kill["reason"] == "max_name_weight"
    assert supervisor.snapshot.last_kill["flattened"] is True


def test_start_sleeve_without_overlay_does_not_flatten_live_book_inside_name_cap(
    tmp_path: Path,
):
    broker = FakeBroker(equity=10_000.0)
    broker.positions = {"AAPL": 15.0}
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    held = supervisor.start_sleeve("asb_test", 0.25)
    assert held is False
    assert supervisor.state != SupervisorState.STOPPED
    assert broker.close_all_count == 0
```

In `tests/alphastrategy/test_api.py` after `test_put_risk_flattens_when_live_book_breaches` add:

```python
def test_put_risk_overlay_while_idle_does_not_flatten_live_book(api_stack):
    client, home, supervisor, broker = api_stack
    bundle_dir = home.imported_dir() / "asb_x"
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")
    broker.positions = {"AAPL": 15.0}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor._persist()
    response = client.put(
        "/api/risk",
        json={"sleeves": {"asb_x": {"max_name_weight": 0.05}}},
    )
    assert response.status == 200
    body = response.json()
    assert body["ok"] is True
    assert body["flattened"] is False
    assert supervisor.state != SupervisorState.STOPPED
    assert broker.close_all_count == 0


def test_put_risk_overlay_while_allocated_flattens_live_book(api_stack):
    client, home, supervisor, broker = api_stack
    bundle_dir = home.imported_dir() / "asb_x"
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")
    start = client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.25})
    assert start.status == 200
    broker.positions = {"AAPL": 15.0}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor._persist()
    response = client.put(
        "/api/risk",
        json={"sleeves": {"asb_x": {"max_name_weight": 0.05}}},
    )
    assert response.status == 200
    body = response.json()
    assert body["ok"] is True
    assert body["flattened"] is True
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1


def test_start_flattens_when_idle_overlay_breaches_live_book(api_stack):
    client, home, supervisor, broker = api_stack
    bundle_dir = home.imported_dir() / "asb_x"
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")
    overlay = client.put(
        "/api/risk",
        json={"sleeves": {"asb_x": {"max_name_weight": 0.05}}},
    )
    assert overlay.status == 200
    assert overlay.json()["flattened"] is False
    broker.positions = {"AAPL": 15.0}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor._persist()
    response = client.post(
        "/api/paper/start",
        json={"bundle_id": "asb_x", "allocation": 0.25},
    )
    assert response.status == 200
    body = response.json()
    assert body["ok"] is True
    assert body["held"] is False
    assert body["flattened"] is True
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1
```

Also assert `test_start_while_halted_returns_held` body `flattened is False`.

In `tests/alphastrategy/test_cli.py` after `test_paper_start_while_halted_prints_held` add:

```python
def test_paper_start_overlay_breach_prints_flattened(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    import yaml

    bundle_dir = _create_imported_bundle(cli_home)
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")
    home = AlphaStrategyHome.from_env()
    home.runtime_path().write_text(
        yaml.safe_dump({"sleeve_overlays": {"asb_test": {"max_name_weight": 0.05}}}),
        encoding="utf-8",
    )
    supervisor = Supervisor(
        home=home,
        broker=FakeBroker(),
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.snapshot.last_got = {"AAPL": 0.15}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor._persist()
    rc = main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    err = captured.err.lower()
    assert "flattened:" in err
    assert "sleeve overlay" in err
    assert "flattens now" in err
```

`REQUIRED_PHRASES` add `"A sleeve overlay that breaches the live book flattens now"`.

In `tests/alphastrategy/test_web_tokens.py` after `test_css_risk_tighten_hint_warn_token` add:

```python
def test_html_risk_overlay_live_book_hint(html_text: str) -> None:
    risk = html_text[html_text.find('id="screen-risk"') :]
    overlays = risk[risk.find('id="risk-overlays"') :]
    assert 'id="risk-overlay-hint"' in overlays
    assert "A sleeve overlay that breaches the live book flattens now." in overlays
    assert overlays.find("risk-overlay-idle") < overlays.find('id="risk-overlay-hint"')
    assert overlays.find('id="risk-overlay-hint"') < overlays.find('id="risk-sleeves"')
    sleeves_onward = overlays[overlays.find('id="risk-sleeves"') :]
    assert 'id="risk-overlay-hint"' not in sleeves_onward
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_css_risk_overlay_hint_warn_token(css_text: str) -> None:
    warn = re.search(r"#risk-overlay-hint\.warn\s*\{[^}]*\}", css_text)
    assert warn is not None and "#f59e0b" in warn.group(0).lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_flattens_when_idle_overlay_breaches_live_book \
  tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_without_overlay_does_not_flatten_live_book_inside_name_cap \
  tests/alphastrategy/test_api.py::test_put_risk_overlay_while_idle_does_not_flatten_live_book \
  tests/alphastrategy/test_api.py::test_put_risk_overlay_while_allocated_flattens_live_book \
  tests/alphastrategy/test_api.py::test_start_flattens_when_idle_overlay_breaches_live_book \
  tests/alphastrategy/test_cli.py::test_paper_start_overlay_breach_prints_flattened \
  tests/alphastrategy/test_web_tokens.py::test_html_risk_overlay_live_book_hint \
  tests/alphastrategy/test_web_tokens.py::test_css_risk_overlay_hint_warn_token \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected FAIL reasons:

- `test_start_sleeve_flattens_when_idle_overlay_breaches_live_book`: state not STOPPED / close_all_count 0
- `test_start_flattens_when_idle_overlay_breaches_live_book`: `flattened` missing or false
- HTML/CSS/help: id or phrase missing

Lock tests that may **PASS on RED** (keep them):

- `test_start_sleeve_without_overlay_does_not_flatten_live_book_inside_name_cap`
- `test_put_risk_overlay_while_idle_does_not_flatten_live_book`
- `test_put_risk_overlay_while_allocated_flattens_live_book` (PUT already enforces while allocated)

If a lock test fails on RED, stop and fix the test, not production code.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-overlay-start-requirements.md \
  docs/plans/2026-08-20-alphastrategy-overlay-start-technical-design.md \
  tests/alphastrategy/test_halt_flatten.py tests/alphastrategy/test_api.py \
  tests/alphastrategy/test_cli.py tests/alphastrategy/test_web_tokens.py \
  tests/alphastrategy/test_helptext.py
git commit -m "test: require overlay-on-start to flatten a breaching live book"
```

---

### Task 2: Engine + API + CLI

**Files:** `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/cli/main.py`

- [ ] **Step 1: `start_sleeve` enforces after persist**

In `start_sleeve`, after `_persist()`, still inside `with self._lock:`:

```python
            self._audit("paper_start", bundle_id=bundle_id, allocation=allocation)
            self._persist()
            self._enforce_live_book()
            return self._snapshot.state == SupervisorState.HALTED
```

Do not take the lock again. `_enforce_live_book` is the internal unlocked helper. Public `enforce_live_book()` stays for the API overlay path.

- [ ] **Step 2: POST /api/paper/start returns flattened**

```python
        held = supervisor.start_sleeve(bundle_id, allocation)
        flattened = supervisor.state in (
            SupervisorState.FLATTENING,
            SupervisorState.STOPPED,
        )
        _json_response(handler, 200, {"ok": True, "held": held, "flattened": flattened})
```

- [ ] **Step 3: CLI stderr**

Next to `_HELD_START`:

```python
_FLAT_START = (
    "flattened: a sleeve overlay that breaches the live book flattens now."
)
```

In `_cmd_paper_start`, control-plane and local paths:

```python
            if payload.get("flattened"):
                print(_FLAT_START, file=sys.stderr)
            elif payload.get("held"):
                print(_HELD_START, file=sys.stderr)
```

```python
        held = supervisor.start_sleeve(bundle_id, allocation)
        flattened = supervisor.state in (
            SupervisorState.FLATTENING,
            SupervisorState.STOPPED,
        )
        if flattened:
            print(_FLAT_START, file=sys.stderr)
        elif held:
            print(_HELD_START, file=sys.stderr)
        return 0
```

Never print start JSON on stdout.

- [ ] **Step 4: Run engine/API/CLI tests**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_flattens_when_idle_overlay_breaches_live_book \
  tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_without_overlay_does_not_flatten_live_book_inside_name_cap \
  tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_while_halted_stays_halted_without_catchup \
  tests/alphastrategy/test_api.py::test_put_risk_overlay_while_idle_does_not_flatten_live_book \
  tests/alphastrategy/test_api.py::test_put_risk_overlay_while_allocated_flattens_live_book \
  tests/alphastrategy/test_api.py::test_start_flattens_when_idle_overlay_breaches_live_book \
  tests/alphastrategy/test_api.py::test_start_while_halted_returns_held \
  tests/alphastrategy/test_cli.py::test_paper_start_overlay_breach_prints_flattened \
  tests/alphastrategy/test_cli.py::test_paper_start_while_halted_prints_held \
  tests/alphastrategy/test_cli.py::test_status_prints_json -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/supervisor/loop.py src/alphastrategy/api/handlers.py src/alphastrategy/cli/main.py
git commit -m "feat: flatten now when Start paper speaks a breaching overlay"
```

---

### Task 3: Hint, help, README

- [ ] **Step 1: HTML** in `#risk-overlays` after the metrics-4 block, before `<div id="risk-sleeves">`:

```html
        <p id="risk-overlay-hint" class="warn">A sleeve overlay that breaches the live book flattens now.</p>
```

- [ ] **Step 2: CSS** after `#risk-tighten-hint.warn`:

```css
#risk-overlay-hint.warn {
  color: #f59e0b;
}
```

- [ ] **Step 3: Help / README**

`how_risk` after overlay-card sentences: `A sleeve overlay that breaches the live book flattens now. `

`how_run` after Start paper while halted: same.

`task_start` after the halted sentence: same.

`task_tighten` after Tighten live-book sentence: same.

`halt_flatten` after Tighten live-book sentence: same.

README Operator (risk/flatten bullets): `A sleeve overlay that breaches the live book flattens now.`

- [ ] **Step 4: Run**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_web_tokens.py::test_html_risk_overlay_live_book_hint \
  tests/alphastrategy/test_web_tokens.py::test_css_risk_overlay_hint_warn_token \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases \
  tests/alphastrategy/test_web_tokens.py::test_html_has_no_live_toggle_label -q
```

Expected: PASS. `"Gross cap"` still not in assembled JS.

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/web/static/index.html src/alphastrategy/web/static/styles.css src/alphastrategy/helptext.py README.md
git commit -m "feat: warn that a breaching sleeve overlay flattens now"
```

---

### Task 4: Full suite

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

Expected: all passed.

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| start_sleeve flatten on idle overlay + live book | 1–2 |
| no flatten without overlay / idle PUT | 1–2 |
| PUT overlay while allocated flattens | 1–2 |
| start API flattened + CLI stderr | 2 |
| Hint + CSS | 3 |
| Help / README | 3 |

No placeholders. No heartbeat flatten. No 409 on start.
