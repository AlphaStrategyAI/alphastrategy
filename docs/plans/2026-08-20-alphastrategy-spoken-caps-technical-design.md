# Spoken Caps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Caps, Headroom, Gross rail, and Positions at-cap use the spoken flatten policy (allocated envelope ∩ overlay), while Tighten still edits writable account policy.

**Architecture:** Public `Supervisor.spoken_policy()` is `_rebalance_policy()`. `from_supervisor` and `GET /api/risk` `spoken` consume it. Caps paints `risk.spoken` with warn when tighter than `account`. Utilization includes `max_name_weight`.

**Tech Stack:** Supervisor, utilization, local HTTP API, Quiet cockpit JS/CSS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-spoken-caps-requirements.md`](../requirements/2026-08-20-alphastrategy-spoken-caps-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. Do not 409 GET/PUT risk.
- Idle overlays stay unpublished (`allocation <= 0`).
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/js/paint-risk.js`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

In `tests/alphastrategy/test_risk.py` after `test_summarize_counts_live_nonzero_positions` assert `max_name_weight`:

```python
    assert out["max_name_weight"] == 0.20
```

Add:

```python
def test_from_supervisor_uses_spoken_policy() -> None:
    from alphastrategy.risk.utilization import from_supervisor

    class Snap:
        orders_today = 0
        last_combined = {}
        last_got = {}

    class Fake:
        policy = AccountPolicy.defaults()
        snapshot = Snap()

        def spoken_policy(self):
            return replace(AccountPolicy.defaults(), max_name_weight=0.05, max_names=10)

    out = from_supervisor(Fake(), live=False)
    assert out["max_name_weight"] == 0.05
    assert out["max_names"] == 10
    assert out["max_gross"] == 1.0
```

In `tests/alphastrategy/test_api.py` after `test_start_flattens_when_idle_overlay_breaches_live_book` add:

```python
def test_get_risk_spoken_follows_allocated_overlay(api_stack):
    client, home, supervisor, _broker = api_stack
    bundle_dir = home.imported_dir() / "asb_x"
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")
    overlay = client.put(
        "/api/risk",
        json={"sleeves": {"asb_x": {"max_name_weight": 0.05, "max_names": 10}}},
    )
    assert overlay.status == 200
    idle = client.get("/api/risk").json()
    assert idle["account"]["max_name_weight"] == 0.20
    assert idle["spoken"]["max_name_weight"] == 0.20
    assert idle["utilization"]["max_name_weight"] == 0.20
    assert idle["spoken"]["max_names"] == 50
    start = client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.25})
    assert start.status == 200
    spoken = client.get("/api/risk").json()
    assert spoken["account"]["max_name_weight"] == 0.20
    assert spoken["account"]["max_names"] == 50
    assert spoken["spoken"]["max_name_weight"] == 0.05
    assert spoken["spoken"]["max_names"] == 10
    assert spoken["utilization"]["max_name_weight"] == 0.05
    assert spoken["utilization"]["max_names"] == 10
    status = client.get("/api/status").json()
    assert status["utilization"]["max_name_weight"] == 0.05
    assert status["utilization"]["max_names"] == 10
```

`REQUIRED_PHRASES` add `"Caps is the spoken book"`.

In `tests/alphastrategy/test_web_tokens.py` after `test_js_paints_risk_caps_tiles` add:

```python
def test_js_paints_risk_caps_from_spoken(js_text: str) -> None:
    render = js_text[js_text.find("function renderRisk") :]
    caps_call = render.split("function renderRiskUtilization")[0] if False else render
    assert "risk.spoken" in render[:800] or "spoken" in js_text[
        js_text.find("function renderRiskCaps") : js_text.find("function buildRiskInputs")
    ]
    paint_risk = js_text[js_text.find("function renderRisk(") :]
    head = paint_risk[: paint_risk.find("function riskFormIsDirty") if False else 900]
    assert "spoken" in paint_risk.split("if (riskFormIsDirty())")[0]
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_gross_and_name_rails_use_spoken_caps(js_text: str) -> None:
    rails = js_text[
        js_text.find("function renderGrossUtilization") : js_text.find("function renderRemainingBudgets")
    ]
    assert "max_gross" in rails
    assert "risk.account && state.risk.account.max_gross" not in rails
    port = js_text[js_text.find("function renderPortfolio") :]
    assert "spokenPolicy" in js_text or "risk.spoken" in port
    assert "Gross cap" not in js_text


def test_css_risk_cap_spoken_warn_token(css_text: str) -> None:
    name = re.search(r"#risk-cap-name\.warn\s*\{[^}]*\}", css_text)
    assert name is not None and "#f59e0b" in name.group(0).lower()
```

Make the JS tests precise (avoid the `if False` junk). Use:

```python
def test_js_paints_risk_caps_from_spoken(js_text: str) -> None:
    render = js_text[js_text.find("function renderRisk(") : js_text.find("function onRiskAccountSubmit")]
    pre_dirty = render.split("if (riskFormIsDirty())")[0]
    assert "spoken" in pre_dirty
    assert "renderRiskCaps" in pre_dirty
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_gross_and_name_rails_use_spoken_caps(js_text: str) -> None:
    rails = js_text[
        js_text.find("function renderGrossUtilization") : js_text.find("function renderRemainingBudgets")
    ]
    assert "utilization()" in rails
    assert "max_gross" in rails
    assert "state.risk.account.max_gross" not in rails
    port = js_text[
        js_text.find("const posBody") : js_text.find("function pulseLabel")
    ]
    assert "spokenPolicy()" in port or "utilization().max_name_weight" in port
    glance = js_text[
        js_text.find("function renderPositionsGlance") : js_text.find("function renderBanners")
    ]
    assert "spokenPolicy()" in glance or "max_name_weight" in glance
    assert "state.risk.account.max_name_weight" not in port
    assert "state.risk.account.max_name_weight" not in glance
    assert "Gross cap" not in js_text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_risk.py::test_from_supervisor_uses_spoken_policy \
  tests/alphastrategy/test_risk.py::test_summarize_counts_live_nonzero_positions \
  tests/alphastrategy/test_api.py::test_get_risk_spoken_follows_allocated_overlay \
  tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_caps_from_spoken \
  tests/alphastrategy/test_web_tokens.py::test_js_gross_and_name_rails_use_spoken_caps \
  tests/alphastrategy/test_web_tokens.py::test_css_risk_cap_spoken_warn_token \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL on missing `spoken`, `max_name_weight` on utilization, JS still reading `risk.account`, phrase missing.

Idle-vs-allocated assertions in the API test fail together until engine+API exist; that is one test.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-spoken-caps-requirements.md \
  docs/plans/2026-08-20-alphastrategy-spoken-caps-technical-design.md \
  tests/alphastrategy/test_risk.py tests/alphastrategy/test_api.py \
  tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_helptext.py
git commit -m "test: require Caps and utilization to use the spoken book"
```

---

### Task 2: Engine + API

**Files:** `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/api/handlers.py`

- [ ] **Step 1: `spoken_policy`**

Next to `_rebalance_policy`:

```python
    def spoken_policy(self) -> AccountPolicy:
        with self._lock:
            return self._rebalance_policy()
```

- [ ] **Step 2: utilization**

In `summarize` return dict add `"max_name_weight": float(policy.max_name_weight)`.

In `from_supervisor`:

```python
    policy = supervisor.spoken_policy()
    return summarize(
        policy=policy,
        ...
    )
```

- [ ] **Step 3: GET /api/risk**

```python
            "account": _policy_to_dict(supervisor.policy),
            "spoken": _policy_to_dict(supervisor.spoken_policy()),
            "defaults": _policy_to_dict(AccountPolicy.defaults()),
```

- [ ] **Step 4: Run**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_risk.py::test_from_supervisor_uses_spoken_policy \
  tests/alphastrategy/test_risk.py::test_summarize_counts_live_nonzero_positions \
  tests/alphastrategy/test_api.py::test_get_risk_spoken_follows_allocated_overlay \
  tests/alphastrategy/test_api.py::test_status_and_risk_include_utilization -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/supervisor/loop.py src/alphastrategy/risk/utilization.py src/alphastrategy/api/handlers.py
git commit -m "feat: expose spoken flatten policy on risk and utilization"
```

---

### Task 3: Paint, help, README

- [ ] **Step 1: `spokenPolicy` in `paint-rails.js`**

After `utilization()`:

```javascript
  function spokenPolicy() {
    return (
      (state.risk && state.risk.spoken) ||
      (state.risk && state.risk.account) ||
      {}
    );
  }
```

`renderGrossUtilization`:

```javascript
  function renderGrossUtilization(gross) {
    const bar = document.getElementById("metric-gross-bar");
    const util = utilization();
    const spoken = spokenPolicy();
    const cap = Number(util.max_gross) || Number(spoken.max_gross);
    const limit = cap > 0 ? cap : 1;
    paintUtilTrack(bar, gross, limit, `gross ${fmtPct(gross)} of cap ${fmtPct(limit)}`);
  }
```

- [ ] **Step 2: Portfolio name cap**

Replace both `state.risk.account.max_name_weight` sites with:

```javascript
      const cap =
        Number(spokenPolicy().max_name_weight) ||
        Number(utilization().max_name_weight) ||
        0.2;
```

- [ ] **Step 3: Caps paint**

`renderRiskCaps(container, policy, account)`: after filling values, if `account` is present and a numeric cap is tighter (smaller max_gross / max_name_weight / max_names / max_orders_per_day), add class `warn` on that metric-value; otherwise remove `warn`.

`renderRisk`:

```javascript
    const spoken = (risk && risk.spoken) || (risk && risk.account) || {};
    renderRiskCaps(document.getElementById("risk-account-caps"), spoken, risk.account);
```

Tighten form still `risk.account`.

- [ ] **Step 4: CSS**

```css
#risk-cap-gross.warn,
#risk-cap-name.warn,
#risk-cap-names.warn,
#risk-cap-orders.warn {
  color: #f59e0b;
}
```

- [ ] **Step 5: Help / README**

`how_risk` after Caps four-tiles sentence: `Caps is the spoken book. Tighten still edits the account form. `

Cockpit body after `Caps is Gross cap / Name cap / Names / Orders today.`: same Caps is the spoken book sentence.

README Caps line: `Caps is the spoken book.`

- [ ] **Step 6: Run**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_caps_from_spoken \
  tests/alphastrategy/test_web_tokens.py::test_js_gross_and_name_rails_use_spoken_caps \
  tests/alphastrategy/test_web_tokens.py::test_css_risk_cap_spoken_warn_token \
  tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_caps_tiles \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases \
  tests/alphastrategy/test_web_tokens.py::test_html_has_no_live_toggle_label -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/alphastrategy/web/static/js/paint-rails.js src/alphastrategy/web/static/js/paint-portfolio.js src/alphastrategy/web/static/js/paint-risk.js src/alphastrategy/web/static/styles.css src/alphastrategy/helptext.py README.md
git commit -m "feat: paint Caps and rails from the spoken book"
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
| spoken_policy + GET spoken | 1–2 |
| idle overlay unpublished | 1–2 |
| utilization spoken + max_name_weight | 1–2 |
| Caps paint + warn | 3 |
| Gross / name rails | 3 |
| Help / README | 3 |

No placeholders. No heartbeat flatten. Tighten stays on account.
