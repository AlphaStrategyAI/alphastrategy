# Run sleeves name contribution last against next Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run sleeve cards name contribution last against next, Remaining is a spoken rail, and Activity `paper_start` names allocation.

**Architecture:** Extract `formatContributionInner` for Portfolio cells and Run cards. Remaining bar fills with spoken share of 1. Blotter `paper_start` uses existing audit `allocation`.

**Tech Stack:** Python 3.9+, pytest, cockpit JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-run-contrib-requirements.md`](../requirements/2026-08-21-alphastrategy-run-contrib-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET.
- Do not seed on `resume()`.
- Keep Run Sleeves four tiles Remaining / Spoken / Active / Idle.
- `paint-portfolio.js` and `paint-rails.js` stay ≤ 400 lines.
- Keep exact `Start paper while halted waits for resume. Resume does not catch up.`
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Create: `docs/requirements/2026-08-21-alphastrategy-run-contrib-requirements.md`
- Create: `docs/plans/2026-08-21-alphastrategy-run-contrib-technical-design.md`
- Modify: `src/alphastrategy/web/static/js/core.js`
- Modify: `src/alphastrategy/web/static/js/paint-run.js`
- Modify: `src/alphastrategy/web/static/js/paint-activity.js`
- Modify: `src/alphastrategy/web/static/index.html`
- Modify: `src/alphastrategy/web/static/styles.css` (only if Remaining bar needs a local rule; prefer existing `.util-track`)
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_web_tokens.py`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` after `Paper count warns when a paper sleeve has no last weights`:

```python
    "Run sleeves name contribution last against next",
    "Run Remaining is a rail",
    "Activity paper_start names allocation",
```

Update `test_js_paints_sleeves_contribution_last` helper slice to start at `function formatContributionInner` and still require `formatWeightsWaitSub`, `"last "`, and the Portfolio `formatContributionCell(contrib[id], lastContrib[id], id, sleeves[id])` call.

In `test_html_run_kill_switch_zones`, after `id="run-remaining"`:

```python
    assert 'id="run-remaining-bar"' in book
```

After `test_js_paints_run_capacity`:

```python
def test_js_run_sleeves_name_contribution(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRunSleeves") : js_text.find("function renderRunStartHint")
    ]
    assert "formatContributionInner" in paint
    assert "sleeve_contribution" in paint
    assert "last_sleeve_contribution" in paint
    assert "run-remaining-bar" in paint
    assert "paintUtilTrack" in paint
    assert "spoken " in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_activity_paper_start_names_allocation(js_text: str) -> None:
    summary = js_text[
        js_text.find("function eventSummary") : js_text.find("function renderActivity")
    ]
    start = summary.split('case "paper_start":')[1].split('case "paper_stop":')[0]
    assert "fmtPct(ev.allocation)" in start
    detail = summary.split('kind === "paper_start"')[1].split('kind === "halt"')[0]
    assert '["Allocation"' in detail
    assert "fmtPct(ev.allocation)" in detail
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

The detail slice must match real `eventDetail` structure. If `paper_start` shares a branch with `paper_stop`, split on `kind === "paper_start"` inside `eventDetail`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_js_run_sleeves_name_contribution tests/alphastrategy/test_web_tokens.py::test_js_activity_paper_start_names_allocation tests/alphastrategy/test_web_tokens.py::test_html_run_kill_switch_zones tests/alphastrategy/test_web_tokens.py::test_js_paints_sleeves_contribution_last -q`

Expected: FAIL.

- [ ] **Step 3: Commit tests and docs**

```bash
git commit -m "test: Run sleeves name contribution last against next"
```

---

### Task 2: Paint, help

- [ ] **Step 1: `formatContributionInner` in `core.js` immediately before `formatContributionCell`**

```javascript
  function formatContributionInner(nextMap, lastMap, bundleId, alloc) {
    const wait = formatWeightsWaitSub(bundleId, alloc);
    if (wait) return wait;
    const nextText = fmtContribution(nextMap);
    const lastText = fmtContribution(lastMap);
    const hasLast = lastMap && typeof lastMap === "object" && Object.keys(lastMap).length;
    const differs = Boolean(hasLast && lastText !== nextText);
    const sub = differs
      ? `<div class="metric-sub nums">` + "last " + lastText + `</div>`
      : "";
    return nextText + sub;
  }

  function formatContributionCell(nextMap, lastMap, bundleId, alloc) {
    return `<td class="nums">${formatContributionInner(nextMap, lastMap, bundleId, alloc)}</td>`;
  }
```

- [ ] **Step 2: HTML Remaining bar**

Under `#run-remaining`:

```html
            <div id="run-remaining" class="metric-value">—</div>
            <div id="run-remaining-bar" class="util-track hidden" aria-hidden="true"></div>
```

- [ ] **Step 3: Run paint**

After remaining/spoken counts, before empty return:

```javascript
    const remBar = document.getElementById("run-remaining-bar");
    if (remBar) {
      paintUtilTrack(remBar, spoken, 1, "spoken " + fmtPct(spoken));
    }
```

In the card template, replace `${formatWeightsWaitSub(id, alloc)}` with contribution from portfolio:

```javascript
    const contrib = (state.portfolio && state.portfolio.sleeve_contribution) || {};
    const lastContrib = (state.portfolio && state.portfolio.last_sleeve_contribution) || {};
```

inside the id loop (or once before the loop):

```javascript
        ${formatContributionInner(contrib[id], lastContrib[id], id, alloc)}
```

Keep the allocation rail. Do not also call `formatWeightsWaitSub` on the card (inner already waits).

- [ ] **Step 4: Activity**

`eventSummary`:

```javascript
      case "paper_start":
        return `${ev.bundle_id || ""} ${fmtPct(ev.allocation)}`.trim();
      case "paper_stop":
      case "import":
        return ev.bundle_id || ev.scope || "";
```

`eventDetail` — split `paper_start` from stop/import:

```javascript
    if (kind === "paper_start") {
      wrap.appendChild(
        detailList([
          ["Bundle", ev.bundle_id || ev.scope],
          ["Allocation", fmtPct(ev.allocation)],
        ])
      );
      return wrap;
    }
    if (kind === "paper_stop" || kind === "import") {
      wrap.appendChild(detailList([["Bundle", ev.bundle_id || ev.scope]]));
      return wrap;
    }
```

Keep `["Allocation"` as that token for the test.

- [ ] **Step 5: Help / README**

`how_run` after `Allocation is a rail. `:

```text
Run sleeves name contribution last against next. Run Remaining is a rail.
```

`cockpit` after `Run Sleeves is Remaining / Spoken / Active / Idle. `:

```text
Run sleeves name contribution last against next.
```

`how_activity` after halt-rows sentence:

```text
Activity paper_start names allocation.
```

README Operator after Sleeves / Paper count sentences.

- [ ] **Step 6: Full tests and commit**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

```bash
git commit -m "feat: Run sleeves name contribution last against next"
```
