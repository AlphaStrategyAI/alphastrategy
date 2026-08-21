# Sleeve overlays name contribution last against next Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Risk sleeve overlay cards name imported / paper / halted / stopped and contribution last against next; overlay Spoken is a spoken rail.

**Architecture:** Reuse `sleeveState` and `formatContributionInner`. Spoken bar fills with spoken share of 1, same as Run Remaining.

**Tech Stack:** Python 3.9+, pytest, cockpit JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-overlay-contrib-requirements.md`](../requirements/2026-08-21-alphastrategy-overlay-contrib-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET.
- Keep Sleeve overlays four tiles Spoken / Overlays / Tighter / Idle.
- Keep `Tighten this sleeve` details and dirty-form skip.
- `paint-portfolio.js` and `paint-rails.js` stay ≤ 400 lines.
- Do not change CLI BOOK / HALT / LIMIT exact splitlines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Create: `docs/requirements/2026-08-21-alphastrategy-overlay-contrib-requirements.md`
- Create: `docs/plans/2026-08-21-alphastrategy-overlay-contrib-technical-design.md`
- Modify: `src/alphastrategy/web/static/index.html`
- Modify: `src/alphastrategy/web/static/js/paint-risk.js`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_web_tokens.py`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` after `Activity paper_start names allocation`:

```python
    "Sleeve overlays name contribution last against next",
    "Each overlay card names imported, paper, halted, or stopped",
    "Sleeve overlay Spoken is a rail",
```

In `test_html_risk_glance_bands`, after `id="risk-overlay-spoken"`:

```python
    assert 'id="risk-overlay-spoken-bar"' in overlays
```

After `test_js_paints_risk_overlay_glance`:

```python
def test_js_overlay_cards_name_contribution(js_text: str) -> None:
    paint = js_text[js_text.find("function renderRisk") :]
    cards = paint.split("No sleeve overlays")[1]
    assert "sleeveState" in cards
    assert "sleeve-head" in cards
    assert "sleeve-state" in cards
    assert "formatContributionInner" in cards
    assert "sleeve_contribution" in cards
    assert "last_sleeve_contribution" in cards
    glance = js_text[
        js_text.find("function renderOverlayGlance") : js_text.find("function riskFormIsDirty")
    ]
    assert "risk-overlay-spoken-bar" in glance
    assert "paintUtilTrack" in glance
    assert "spoken " in glance
    assert "Tighten this sleeve" in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

Keep `test_js_paints_risk_overlay_glance` `Tighten this sleeve` / `details`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_js_overlay_cards_name_contribution tests/alphastrategy/test_web_tokens.py::test_html_risk_glance_bands -q`

Expected: FAIL.

- [ ] **Step 3: Commit tests and docs**

```bash
git commit -m "test: Sleeve overlays name contribution last against next"
```

---

### Task 2: Paint, help

- [ ] **Step 1: HTML Spoken bar**

Under `#risk-overlay-spoken`:

```html
            <div id="risk-overlay-spoken" class="metric-value">—</div>
            <div id="risk-overlay-spoken-bar" class="util-track hidden" aria-hidden="true"></div>
```

- [ ] **Step 2: `renderOverlayGlance`**

After spoken fail/warn toggles:

```javascript
    const spokenBar = document.getElementById("risk-overlay-spoken-bar");
    if (spokenBar) {
      paintUtilTrack(spokenBar, spoken, 1, "spoken " + fmtPct(spoken));
    }
```

- [ ] **Step 3: Overlay cards in `renderRisk`**

Before the id loop:

```javascript
    const contrib = (state.portfolio && state.portfolio.sleeve_contribution) || {};
    const lastContrib = (state.portfolio && state.portfolio.last_sleeve_contribution) || {};
    const bundles = state.bundles || { imported: [], paper: {} };
```

Replace the `h2` heading with:

```javascript
      const st = sleeveState(id, bundles, state.status);
      const statusClass =
        st === "paper"
          ? "status-running"
          : st === "halted"
            ? "status-halt"
            : st === "stopped"
              ? "status-stopped"
              : "status-muted";
      const head = document.createElement("div");
      head.className = "sleeve-head";
      const heading = document.createElement("h3");
      heading.textContent = id;
      const badge = document.createElement("span");
      badge.className = "sleeve-state " + statusClass;
      badge.textContent = st;
      head.appendChild(heading);
      head.appendChild(badge);
      panel.appendChild(head);
```

Keep Allocation text, `paintUtilTrack`, tighter line. After the allocation track:

```javascript
      const contribEl = document.createElement("div");
      contribEl.className = "nums";
      contribEl.innerHTML = formatContributionInner(contrib[id], lastContrib[id], id, alloc);
      panel.appendChild(contribEl);
```

Keep `Tighten this sleeve` details.

- [ ] **Step 4: Help / README**

`how_risk` after `Spoken is the hero. `: `Sleeve overlay Spoken is a rail. `

After `Each overlay card is allocation rail and tighter count; Tighten this sleeve holds the form. `:

```text
Each overlay card names imported, paper, halted, or stopped. Sleeve overlays name contribution last against next.
```

`cockpit` after `Risk lists sleeve overlays as Spoken / Overlays / Tighter / Idle. `: `Sleeve overlays name contribution last against next. `

README Operator after `Run Remaining is a rail.`

- [ ] **Step 5: Full tests and commit**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

```bash
git commit -m "feat: Sleeve overlays name contribution last against next"
```
