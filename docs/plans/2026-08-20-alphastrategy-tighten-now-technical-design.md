# Tighten Live Book Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the operator tightens a flatten-critical cap below the live book, flatten now instead of waiting for the next legal rebalance.

**Architecture:** After `set_policy` (and after sleeve overlays hit `runtime.yaml`), `check_book` on live got weights (priced qty, else `last_got`, else `last_combined`) against `_rebalance_policy()`. Same flatten + `KillOutcome` as a rebalance limit breach. Heartbeat unchanged.

**Tech Stack:** Supervisor, `check_book`, local HTTP API, Quiet cockpit HTML/CSS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-tighten-now-requirements.md`](../requirements/2026-08-20-alphastrategy-tighten-now-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten and does not place orders.
- Do not retry leftover orders. Do not change halt/flatten/isolate crash recovery.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

In `tests/alphastrategy/test_halt_flatten.py` after `test_start_sleeve_while_halted_stays_halted_without_catchup` add:

```python
def test_set_policy_flattens_when_live_book_breaches_gross(tmp_path: Path):
    broker = FakeBroker(equity=10_000.0)
    broker.positions = {"AAPL": 40.0}
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor.set_policy({"max_gross": 0.1})
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1
    assert supervisor.snapshot.last_kill is not None
    assert supervisor.snapshot.last_kill["reason"] == "max_gross"
    assert supervisor.snapshot.last_kill["flattened"] is True


def test_set_policy_min_delta_does_not_flatten_live_book(tmp_path: Path):
    broker = FakeBroker(equity=10_000.0)
    broker.positions = {"AAPL": 40.0}
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor.set_policy({"min_delta_dollar": 5.0})
    assert supervisor.state != SupervisorState.STOPPED
    assert broker.close_all_count == 0


def test_set_policy_ok_when_live_book_inside_cap(tmp_path: Path):
    broker = FakeBroker(equity=10_000.0)
    broker.positions = {"AAPL": 5.0}
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor.set_policy({"max_gross": 0.1})
    assert supervisor.state != SupervisorState.STOPPED
    assert broker.close_all_count == 0
```

In `tests/alphastrategy/test_api.py` after `test_put_risk_tightens_account_policy` add:

```python
def test_put_risk_flattens_when_live_book_breaches(api_stack):
    client, _home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 40.0}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    response = client.put("/api/risk", json={"account": {"max_gross": 0.1}})
    assert response.status == 200
    body = response.json()
    assert body["ok"] is True
    assert body["flattened"] is True
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1
```

Also assert existing `test_put_risk_tightens_account_policy` body may include `flattened is False` (add that assertion on the 200 response).

`REQUIRED_PHRASES` add `"Tighten that breaches the live book flattens now"`.

In `tests/alphastrategy/test_web_tokens.py`:

```python
def test_html_risk_tighten_live_book_hint(html_text: str) -> None:
    risk = html_text[html_text.find('id="screen-risk"') :]
    tighten = risk[risk.find('id="risk-tighten"') : risk.find('id="risk-overlays"')]
    assert 'id="risk-tighten-hint"' in tighten
    assert "Tighten that breaches the live book flattens now." in tighten
    assert tighten.find("risk-tighten-fields") < tighten.find('id="risk-tighten-hint"')
    assert tighten.find('id="risk-tighten-hint"') < tighten.find('id="risk-account-form"')
    assert 'id="risk-tighten-hint"' not in risk[risk.find('id="risk-account-form"') :]
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_css_risk_tighten_hint_warn_token(css_text: str) -> None:
    warn = re.search(r"#risk-tighten-hint\.warn\s*\{[^}]*\}", css_text)
    assert warn is not None and "#f59e0b" in warn.group(0).lower()
```

In `test_e2e_mocked.py` `test_v1_done_path`, after `set_policy({"max_gross": 0.1})` the flatten may already have run. Keep `assert broker.close_all_count == 1` after the close-window tick (still 1). Optionally assert state is STOPPED immediately after `set_policy` **before** `advance_now`:

```python
    supervisor.set_policy({"max_gross": 0.1})
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1
    broker.advance_now(session_close - timedelta(minutes=10))
    supervisor.tick()
    assert broker.close_all_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_set_policy_flattens_when_live_book_breaches_gross tests/alphastrategy/test_halt_flatten.py::test_set_policy_min_delta_does_not_flatten_live_book tests/alphastrategy/test_api.py::test_put_risk_flattens_when_live_book_breaches tests/alphastrategy/test_web_tokens.py::test_html_risk_tighten_live_book_hint tests/alphastrategy/test_web_tokens.py::test_css_risk_tighten_hint_warn_token tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_e2e_mocked.py::test_v1_done_path -q
```

Expected: FAIL (`set_policy` does not flatten; HTML id missing; phrase missing). `min_delta` test should **pass** today (no flatten) — if it fails, stop and fix the test.

If `test_set_policy_min_delta_does_not_flatten_live_book` PASSES on RED run, that is correct (existing behavior). Keep it as a lock. The gross test must FAIL.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-tighten-now-requirements.md docs/plans/2026-08-20-alphastrategy-tighten-now-technical-design.md tests/alphastrategy/test_halt_flatten.py tests/alphastrategy/test_api.py tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_helptext.py tests/alphastrategy/test_e2e_mocked.py
git commit -m "test: require Tighten on a breaching live book to flatten now"
```

---

### Task 2: Engine + API

**Files:** `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/api/handlers.py`

- [ ] **Step 1: `_live_book_weights` + `_enforce_live_book` + public `enforce_live_book`**

Inside `Supervisor`, next to `set_policy`:

```python
    def set_policy(self, overlay: dict) -> None:
        """Apply a tighten-only overlay patch to the account policy."""
        with self._lock:
            self._policy = merge_limits({}, self._policy, overlay)
            self._enforce_live_book()

    def enforce_live_book(self) -> None:
        with self._lock:
            self._enforce_live_book()

    def _live_book_weights(self, equity: float) -> dict[str, float]:
        positions = _positions_map(self._broker.list_positions())
        prices = dict(self._snapshot.last_prices)
        if equity > 0 and prices:
            got = {
                symbol: (qty * prices[symbol]) / equity
                for symbol, qty in positions.items()
                if symbol in prices
            }
            if got:
                return got
        if self._snapshot.last_got:
            return dict(self._snapshot.last_got)
        return dict(self._snapshot.last_combined)

    def _enforce_live_book(self) -> None:
        if self._snapshot.state in (
            SupervisorState.FLATTENING,
            SupervisorState.STOPPED,
        ):
            return
        try:
            equity = self._equity()
            weights = self._live_book_weights(equity)
        except Exception as exc:
            self._halt(f"tighten live book: {exc}")
            return
        try:
            check_book(weights, equity, self._rebalance_policy())
        except FlattenRequested as exc:
            reason = exc.reason or "limit"
            self._flatten_account(reason=reason)
            self._record_kill(
                KillOutcome(
                    isolated=False,
                    flattened=True,
                    scope="account",
                    reason=reason,
                    bundle_id=None,
                )
            )
```

- [ ] **Step 2: PUT /api/risk**

After saving runtime, if `sleeves_patch is not None`, call `supervisor.enforce_live_book()`.

Response:

```python
        flattened = supervisor.state in (
            SupervisorState.FLATTENING,
            SupervisorState.STOPPED,
        )
        _json_response(handler, 200, {"ok": True, "flattened": flattened})
```

Import `SupervisorState` in handlers if not already imported (it is).

- [ ] **Step 3: Run engine/API tests**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_set_policy_flattens_when_live_book_breaches_gross tests/alphastrategy/test_halt_flatten.py::test_set_policy_min_delta_does_not_flatten_live_book tests/alphastrategy/test_halt_flatten.py::test_set_policy_ok_when_live_book_inside_cap tests/alphastrategy/test_api.py::test_put_risk_flattens_when_live_book_breaches tests/alphastrategy/test_api.py::test_put_risk_tightens_account_policy tests/alphastrategy/test_e2e_mocked.py::test_v1_done_path -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/alphastrategy/supervisor/loop.py src/alphastrategy/api/handlers.py
git commit -m "feat: flatten now when Tighten breaches the live book"
```

---

### Task 3: Hint, help, README

- [ ] **Step 1: HTML** in `#risk-tighten` after the metrics-4 block, before `<div class="panel">`:

```html
        <p id="risk-tighten-hint" class="warn">Tighten that breaches the live book flattens now.</p>
```

- [ ] **Step 2: CSS** after existing tighten warn rules:

```css
#risk-tighten-hint.warn {
  color: #f59e0b;
}
```

- [ ] **Step 3: Help / README**

`how_risk` body after Tighten-only sentence: `Tighten that breaches the live book flattens now. `

`task_tighten` body after the PUT-keys sentence: same.

`halt_flatten` after limit-breach flatten sentences: same.

README Operator (risk/flatten bullets): `Tighten that breaches the live book flattens now.`

- [ ] **Step 4: Run**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_risk_tighten_live_book_hint tests/alphastrategy/test_web_tokens.py::test_css_risk_tighten_hint_warn_token tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_html_has_no_live_toggle_label -q
```

Expected: PASS. `"Gross cap"` still not in assembled JS.

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/web/static/index.html src/alphastrategy/web/static/styles.css src/alphastrategy/helptext.py README.md
git commit -m "feat: warn on Tighten that a breaching live book flattens now"
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
| Live book gross breach flattens on set_policy | 1–2 |
| min_delta does not flatten | 1–2 |
| PUT flattened flag + sleeve overlay re-enforce | 2 |
| Hint + CSS | 3 |
| Help / README | 3 |
| e2e still one flatten | 1–2 |

No placeholders. No heartbeat flatten.
