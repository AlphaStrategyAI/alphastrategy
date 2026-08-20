# Risk Tighten Glance Tiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paint Risk Tighten as Tight / Delta $ / Delta % / Fields glance tiles, with `GET /api/risk` exposing v1 ship defaults for the Tight count.

**Architecture:** HTML metrics inside `#risk-tighten` before the existing form panel. `renderTightenGlance` fills four mounts from `state.risk.account` vs `state.risk.defaults` using existing `overlayTighterCount`. Handlers add `defaults` on GET and keep ignoring it on PUT.

**Tech Stack:** Quiet cockpit HTML/CSS/JS, FastAPI-style stdlib handlers, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-tighten-glance-requirements.md`](../requirements/2026-08-20-alphastrategy-tighten-glance-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Keep `#risk-caps`, `#risk-headroom`, `#risk-tighten`, `#risk-overlays`, `#risk-account-form`, `#risk-error`. Each JS part ≤ 400 lines.
- Do not clone Caps Gross/Names/Orders onto Tighten. Do not label a tile Live or Tighter.
- `"Gross cap"` must not appear in assembled JS (`test_js_paints_risk_caps_tiles` scans whole `js_text`).
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/api/handlers.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/web/static/js/paint-risk.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: API**

In `tests/alphastrategy/test_api.py`, after `test_get_risk_includes_spoken_labels`, add:

```python
def test_get_risk_includes_v1_defaults(api_client: ApiClient) -> None:
    from dataclasses import asdict

    from alphastrategy.risk.policy import AccountPolicy

    risk = api_client.get("/api/risk").json()
    assert risk["defaults"] == asdict(AccountPolicy.defaults())
    assert risk["account"]["max_gross"] == risk["defaults"]["max_gross"]


def test_put_risk_ignores_defaults_payload(api_client: ApiClient) -> None:
    before = api_client.get("/api/risk").json()
    response = api_client.put(
        "/api/risk",
        json={
            "defaults": {"max_gross": 0.01},
            "account": {"max_name_weight": 0.15},
        },
    )
    assert response.status == 200
    after = api_client.get("/api/risk").json()
    assert after["defaults"] == before["defaults"]
    assert after["account"]["max_name_weight"] == 0.15
    assert after["account"]["max_gross"] == before["account"]["max_gross"]
```

- [ ] **Step 2: HTML/JS/CSS**

In `test_html_risk_glance_bands`, after `assert 'id="risk-account-form"' in tighten`, add:

```python
    assert 'id="risk-tighten-tight"' in tighten
    assert 'id="risk-tighten-delta-dollar"' in tighten
    assert 'id="risk-tighten-delta-frac"' in tighten
    assert 'id="risk-tighten-fields"' in tighten
    assert "metrics-4" in tighten
    assert "hero" in tighten
    assert ">Tight<" in tighten
    assert ">Delta $<" in tighten
    assert ">Delta %<" in tighten
    assert ">Fields<" in tighten
```

Keep `id="risk-account-form"` and `id="risk-error"` asserts. Tight ids must sit in the `tighten` slice, not overlays.

Add:

```python
def test_js_paints_risk_tighten_glance(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderTightenGlance") : js_text.find(
            "function renderOverlayGlance"
        )
    ]
    assert "function renderTightenGlance" in js_text
    assert "risk-tighten-tight" in paint
    assert "risk-tighten-delta-dollar" in paint
    assert "risk-tighten-delta-frac" in paint
    assert "risk-tighten-fields" in paint
    assert "overlayTighterCount" in paint
    assert "min_delta_dollar" in paint
    assert "min_delta_frac" in paint
    assert "NUMERIC_CAPS.length" in paint
    assert "fmtNum" in paint
    assert "fmtPct" in paint
    risk_fn = js_text[js_text.find("function renderRisk") :]
    glance = risk_fn.find("renderTightenGlance")
    dirty = risk_fn.find("if (riskFormIsDirty())")
    assert glance != -1 and dirty != -1 and glance < dirty
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_risk_tighten_tokens(css_text: str) -> None:
    tight = re.search(r"#risk-tighten-tight\.warn\s*\{[^}]*\}", css_text)
    assert tight is not None and "#f59e0b" in tight.group(0).lower()
```

`REQUIRED_PHRASES` add `"Tight / Delta $ / Delta % / Fields"`.

e2e `test_control_plane_serves_help`: `assert 'id="risk-tighten-tight"' in html` and `assert risk_body["defaults"]["max_gross"] == 1.0`.

- [ ] **Step 3: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_get_risk_includes_v1_defaults tests/alphastrategy/test_api.py::test_put_risk_ignores_defaults_payload tests/alphastrategy/test_web_tokens.py::test_html_risk_glance_bands tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_tighten_glance tests/alphastrategy/test_web_tokens.py::test_css_risk_tighten_tokens tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_e2e_mocked.py::test_control_plane_serves_help -q`

Expected: FAIL (`defaults` missing, ids / phrase missing).

---

### Task 2: API, HTML, CSS, JS, help

- [ ] **Step 4: API** — `handle_get_risk` includes `"defaults": _policy_to_dict(AccountPolicy.defaults())`. PUT still reads only `account` and `sleeves`.

- [ ] **Step 5: HTML** — Tighten metrics from the requirements, before the form `.panel`.

- [ ] **Step 6: CSS** — separate `#risk-tighten-tight.warn` block.

- [ ] **Step 7: JS** — `renderTightenGlance(risk)` after `overlayTighterCount`. Fill four tiles (even when the form is dirty). Tight = `overlayTighterCount(account, defaults)` with `warn` when > 0. Delta $ = `fmtNum(..., 2)`. Delta % = `fmtPct`. Fields = `String(NUMERIC_CAPS.length)`. Call it from `renderRisk` before `riskFormIsDirty`.

- [ ] **Step 8: Help + README** — `how_risk` Tight / Delta $ / Delta % / Fields; Tight is the hero; skip floors Caps does not show. Cockpit/README the same.

- [ ] **Step 9: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: PASS.

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| GET `defaults` | 1, 2, 4 |
| PUT ignores `defaults` | 1, 4 |
| Four Tight tiles + hero | 2, 5, 7 |
| Reuse `overlayTighterCount` | 2, 7 |
| Paint while form dirty | 2, 7 |
| Token `#f59e0b` | 2, 6 |
| Help phrase | 2, 8 |
