# Sleeves names when a paper sleeve has no last weights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Portfolio Sleeves Contribution and Strategies Paper count name `weights` when a paper sleeve has no last sleeve weights.

**Architecture:** Reuse `formatWeightsWaitSub` inside `formatContributionCell`. Paper hero uses `warn` instead of `status-running` when any paper allocation is missing last weights.

**Tech Stack:** Python 3.9+, pytest, cockpit JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-sleeves-weights-requirements.md`](../requirements/2026-08-21-alphastrategy-sleeves-weights-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET.
- Do not seed on `resume()`.
- Do not include `"last_sleeve_weights"` on GET `/api/portfolio`.
- Keep Sleeves `colspan='3'`. Keep Roster `colspan='4'`.
- `paint-portfolio.js` and `paint-rails.js` stay ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Create: `docs/requirements/2026-08-21-alphastrategy-sleeves-weights-requirements.md`
- Create: `docs/plans/2026-08-21-alphastrategy-sleeves-weights-technical-design.md`
- Modify: `src/alphastrategy/web/static/js/core.js`
- Modify: `src/alphastrategy/web/static/js/paint-portfolio.js`
- Modify: `src/alphastrategy/web/static/js/paint-strategies.js`
- Modify: `src/alphastrategy/web/static/styles.css`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_web_tokens.py`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` after `Roster names when a paper sleeve has no last weights`:

```python
    "Sleeves names when a paper sleeve has no last weights",
    "Paper count warns when a paper sleeve has no last weights",
```

Update `test_js_paints_sleeves_contribution_last`: helper slice must include `formatWeightsWaitSub`. Portfolio call must pass `id` and `sleeves[id]`.

```python
def test_js_paints_sleeves_contribution_last(js_text: str) -> None:
    assert "function formatContributionCell" in js_text
    helper = js_text[
        js_text.find("function formatContributionCell") : js_text.find("async function api")
    ]
    assert "fmtContribution" in helper
    assert '"last "' in helper
    assert "metric-sub" in helper
    assert "formatWeightsWaitSub" in helper
    port = js_text[
        js_text.find("function renderPortfolio") : js_text.find("function pulseLabel")
    ]
    assert "formatContributionCell(contrib[id], lastContrib[id], id, sleeves[id])" in port
    assert "last_sleeve_contribution" in port
    assert "colspan='9'" in port
    assert "colspan='3'" in port
    assert "Gross cap" not in js_text
    assert "Order size" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

After `test_js_paints_roster_weights_wait`:

```python
def test_js_paper_count_warns_without_last_weights(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderStrategies") : js_text.find("function runFormIsDirty")
    ]
    assert "sleeveHasLastWeights" in paint
    assert '"strat-count-paper"' in paint
    assert '"warn"' in paint
    assert "status-running" in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_sleeves_weights_wait_token(css_text: str) -> None:
    sleeves = re.search(r"#sleeves-table \.metric-sub\.warn\s*\{[^}]*\}", css_text)
    paper = re.search(r"#strat-count-paper\.warn\s*\{[^}]*\}", css_text)
    assert sleeves is not None and "#f59e0b" in sleeves.group(0).lower()
    assert paper is not None and "#f59e0b" in paper.group(0).lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_js_paints_sleeves_contribution_last tests/alphastrategy/test_web_tokens.py::test_js_paper_count_warns_without_last_weights tests/alphastrategy/test_web_tokens.py::test_css_sleeves_weights_wait_token -q`

Expected: FAIL.

- [ ] **Step 3: Commit tests and docs**

```bash
git commit -m "test: Sleeves names when a paper sleeve has no last weights"
```

---

### Task 2: Paint, help

- [ ] **Step 1: `formatContributionCell`**

```javascript
  function formatContributionCell(nextMap, lastMap, bundleId, alloc) {
    const wait = formatWeightsWaitSub(bundleId, alloc);
    if (wait) {
      return `<td class="nums">${wait}</td>`;
    }
    const nextText = fmtContribution(nextMap);
    const lastText = fmtContribution(lastMap);
    const hasLast = lastMap && typeof lastMap === "object" && Object.keys(lastMap).length;
    const differs = Boolean(hasLast && lastText !== nextText);
    const sub = differs
      ? `<div class="metric-sub nums">` + "last " + lastText + `</div>`
      : "";
    return `<td class="nums">${nextText}${sub}</td>`;
  }
```

`formatWeightsWaitSub` already returns `""` when alloc is not `> 0` or weights exist. Passing `undefined` alloc is safe (`Number(undefined)` is `NaN`).

- [ ] **Step 2: Portfolio call**

```javascript
        tr.innerHTML = `<td>${id}</td><td class="nums">${fmtPct(sleeves[id])}</td>` + formatContributionCell(contrib[id], lastContrib[id], id, sleeves[id]);
```

- [ ] **Step 3: Paper count**

In `renderStrategies`, after the count loop, before `setCount`:

```javascript
    let waiting = false;
    for (const id of ids) {
      const alloc = bundles.paper[id] || 0;
      if (Number(alloc) > 0 && !sleeveHasLastWeights(id)) waiting = true;
    }
```

Then `setCount("strat-count-paper", counts.paper, waiting ? "warn" : "status-running");`

Keep other `setCount` calls.

- [ ] **Step 4: CSS**

```css
#sleeves-table .metric-sub.warn {
  color: #f59e0b;
}

#strat-count-paper.warn {
  color: #f59e0b;
}
```

- [ ] **Step 5: Help / README**

`how_portfolio` / `cockpit`: after `Sleeves Contribution names last against next. ` add `Sleeves names when a paper sleeve has no last weights. `

`how_strategies`: after `Roster names when a paper sleeve has no last weights. ` add `Paper count warns when a paper sleeve has no last weights. `

README Operator after Roster sentence.

- [ ] **Step 6: Full tests and commit**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

```bash
git commit -m "feat: Sleeves names when a paper sleeve has no last weights"
```
