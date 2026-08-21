# Roster names when a paper sleeve has no last weights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strategies Roster and Run sleeve cards name `weights` when a paper sleeve has no last sleeve weights, using GET `/api/portfolio` `last_sleeve_weight_ids` without dumping the weight map.

**Architecture:** Glance helper lists ids with a non-empty persisted `last_sleeve_weights` dict. Cockpit paints a warn `weights` sub and a Roster allocation rail. GET does not evaluate DSL and does not flatten.

**Tech Stack:** Python 3.9+, pytest, cockpit JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-roster-weights-requirements.md`](../requirements/2026-08-21-alphastrategy-roster-weights-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET.
- Do not call `_seed_last_sleeve_weights` from `resume()`.
- Do not include `"last_sleeve_weights"` on GET `/api/portfolio`.
- Keep `sleeveState` four words. Keep Roster `colspan='4'`.
- Keep exact `Start paper while halted waits for resume. Resume does not catch up.`
- `paint-portfolio.js` and `paint-rails.js` stay ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Create: `docs/requirements/2026-08-21-alphastrategy-roster-weights-requirements.md`
- Create: `docs/plans/2026-08-21-alphastrategy-roster-weights-technical-design.md`
- Modify: `src/alphastrategy/risk/utilization.py`
- Modify: `src/alphastrategy/api/handlers.py`
- Modify: `src/alphastrategy/web/static/js/core.js`
- Modify: `src/alphastrategy/web/static/js/paint-strategies.js`
- Modify: `src/alphastrategy/web/static/js/paint-run.js`
- Modify: `src/alphastrategy/web/static/styles.css`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`
- Test: `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_risk.py`
- Modify: `tests/alphastrategy/test_api.py`
- Modify: `tests/alphastrategy/test_web_tokens.py`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` after `Roster names imported at`:

```python
    "Roster names when a paper sleeve has no last weights",
```

In `test_risk.py` after `test_from_supervisor_live_limit_unknown_when_paper_sleeve_has_no_last_weights` (keep that test):

```python
def test_last_sleeve_weight_ids_skips_empty_and_sorts() -> None:
    from alphastrategy.risk.utilization import last_sleeve_weight_ids

    class Snap:
        last_sleeve_weights = {
            "asb_z": {},
            "asb_x": {"AAPL": 1.0},
            "asb_y": {"MSFT": 1.0},
        }

    assert last_sleeve_weight_ids(Snap()) == ["asb_x", "asb_y"]


def test_last_sleeve_weight_ids_empty_when_missing() -> None:
    from alphastrategy.risk.utilization import last_sleeve_weight_ids

    class Snap:
        last_sleeve_weights = {}

    assert last_sleeve_weight_ids(Snap()) == []
```

In `test_api.py` after `test_portfolio_omits_next_when_paper_sleeve_has_no_last_weights`:

```python
def test_portfolio_lists_last_sleeve_weight_ids(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_sleeve_weights = {
        "asb_x": {"AAPL": 1.0},
        "asb_z": {},
    }
    supervisor.snapshot.sleeves = {"asb_x": 0.18, "asb_z": 0.10}
    save_state(home.state_path(), supervisor.snapshot)
    close_all_before = broker.close_all_count
    body = client.get("/api/portfolio").json()
    assert body["last_sleeve_weight_ids"] == ["asb_x"]
    assert "last_sleeve_weights" not in body
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"


def test_portfolio_omits_last_sleeve_weight_id_when_paper_sleeve_has_no_last_weights(
    api_stack,
):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.18}
    supervisor.snapshot.last_sleeve_weights = {}
    supervisor.snapshot.sleeves = {"asb_y": 0.18}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    close_all_before = broker.close_all_count
    body = client.get("/api/portfolio").json()
    assert "asb_y" not in body["last_sleeve_weight_ids"]
    assert "last_sleeve_weights" not in body
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"
```

Extend `test_resume_after_seed_failure_keeps_unknown_limit` after the existing assertions:

```python
    book = client.get("/api/portfolio").json()
    assert "asb_z" not in book["last_sleeve_weight_ids"]
    assert "last_sleeve_weights" not in book
    assert broker.close_all_count == close_all_before
```

In `test_web_tokens.py` after `test_js_paints_strategy_inventory`:

```python
def test_js_paints_roster_weights_wait(js_text: str) -> None:
    helper = js_text[
        js_text.find("function sleeveHasLastWeights") : js_text.find("function importedIds")
    ]
    assert "formatWeightsWaitSub" in helper
    assert "last_sleeve_weight_ids" in helper
    assert ">weights<" in helper
    paint = js_text[
        js_text.find("function renderStrategies") : js_text.find("function runFormIsDirty")
    ]
    assert "formatWeightsWaitSub" in paint
    assert "data-alloc-rail" in paint
    assert "paintUtilTrack" in paint
    run = js_text[
        js_text.find("function renderRunSleeves") : js_text.find("function renderRunStartHint")
    ]
    assert "formatWeightsWaitSub" in run
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_roster_weights_wait_token(css_text: str) -> None:
    roster = re.search(
        r"#strategies-table \.metric-sub\.warn\s*\{[^}]*\}", css_text
    )
    card = re.search(r"\.sleeve-card \.metric-sub\.warn\s*\{[^}]*\}", css_text)
    assert roster is not None and "#f59e0b" in roster.group(0).lower()
    assert card is not None and "#f59e0b" in card.group(0).lower()
```

Keep `test_html_strategies_inventory_bands` five screens. Keep `colspan='4'` in `renderStrategies`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py tests/alphastrategy/test_risk.py::test_last_sleeve_weight_ids_skips_empty_and_sorts tests/alphastrategy/test_api.py::test_portfolio_lists_last_sleeve_weight_ids tests/alphastrategy/test_web_tokens.py::test_js_paints_roster_weights_wait -q`

Expected: FAIL (import / missing helper / missing phrase / missing JS).

- [ ] **Step 3: Commit tests and docs**

```bash
git add docs/requirements/2026-08-21-alphastrategy-roster-weights-requirements.md \
  docs/plans/2026-08-21-alphastrategy-roster-weights-technical-design.md \
  tests/alphastrategy/test_helptext.py tests/alphastrategy/test_risk.py \
  tests/alphastrategy/test_api.py tests/alphastrategy/test_web_tokens.py
git commit -m "test: Roster names when a paper sleeve has no last weights"
```

---

### Task 2: Helper, GET, paint, help

**Files:**
- Modify: `src/alphastrategy/risk/utilization.py`
- Modify: `src/alphastrategy/api/handlers.py`
- Modify: `src/alphastrategy/web/static/js/core.js`
- Modify: `src/alphastrategy/web/static/js/paint-strategies.js`
- Modify: `src/alphastrategy/web/static/js/paint-run.js`
- Modify: `src/alphastrategy/web/static/styles.css`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

- [ ] **Step 1: Glance helper**

In `utilization.py` after `_next_send_ready`:

```python
def last_sleeve_weight_ids(snapshot: Any) -> list[str]:
    weights = getattr(snapshot, "last_sleeve_weights", None) or {}
    ids: list[str] = []
    for bundle_id, sleeve_weights in weights.items():
        if isinstance(sleeve_weights, dict) and sleeve_weights:
            ids.append(str(bundle_id))
    return sorted(ids)
```

- [ ] **Step 2: GET portfolio**

Import `last_sleeve_weight_ids`. In `handle_get_portfolio` payload next to `last_sleeve_contribution`:

```python
        "last_sleeve_weight_ids": last_sleeve_weight_ids(snapshot),
```

Do not add `last_sleeve_weights`.

- [ ] **Step 3: JS helpers**

In `core.js` after `hasPaperSleeve`:

```javascript
  function sleeveHasLastWeights(bundleId) {
    const ids = (state.portfolio && state.portfolio.last_sleeve_weight_ids) || [];
    return ids.indexOf(bundleId) >= 0;
  }

  function formatWeightsWaitSub(bundleId, alloc) {
    if (!(Number(alloc) > 0) || sleeveHasLastWeights(bundleId)) return "";
    return `<div class="metric-sub nums warn">weights</div>`;
  }
```

Note: `test_js_paints_roster_weights_wait` slices helper until `function importedIds`. Place `formatWeightsWaitSub` **before** `importedIds` (move the two new functions to sit after `riskSummary` and **before** `importedIds`), or change the slice. Prefer placing them immediately before `importedIds`.

- [ ] **Step 4: Roster paint**

In `renderStrategies` row:

```javascript
        tr.innerHTML = `
        <td>${id}<div class="metric-sub nums">${when}</div></td>
        <td class="status-${statusClass}">${st}</td>
        <td class="nums">${fmtPct(alloc)}<div class="util-track" data-alloc-rail></div>${formatWeightsWaitSub(id, alloc)}</td>
        <td class="muted">${riskSummary(policy)}</td>
      `;
        tbody.appendChild(tr);
        const track = tr.querySelector("[data-alloc-rail]");
        paintUtilTrack(track, alloc, 1, "allocation " + fmtPct(alloc));
```

Keep empty `colspan='4'`.

- [ ] **Step 5: Run cards**

After `paintUtilTrack(track, alloc, 1, "allocation " + fmtPct(alloc));` insert the wait sub into the card template after the rail:

```html
        <div class="util-track" data-alloc-rail></div>
```

becomes that div plus `${formatWeightsWaitSub(id, alloc)}` in the template string.

- [ ] **Step 6: CSS**

After `.metric-sub { ... }`:

```css
#strategies-table .metric-sub.warn,
.sleeve-card .metric-sub.warn {
  color: #f59e0b;
}

#strategies-table .util-track {
  margin-top: 0.35rem;
  max-width: 8rem;
}
```

- [ ] **Step 7: Help / README**

`how_strategies` after `Roster names imported at. `:

```text
Roster names when a paper sleeve has no last weights.
```

`cockpit` after `Paper is the hero count. `:

```text
Roster names when a paper sleeve has no last weights.
```

`how_run` after `Allocation is a rail. `:

```text
Run sleeves name when a paper sleeve has no last weights.
```

README Operator after `Caps LIMIT waits when a paper sleeve has no last weights.`:

```text
Roster names when a paper sleeve has no last weights.
```

- [ ] **Step 8: Run tests**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add src/alphastrategy/risk/utilization.py src/alphastrategy/api/handlers.py \
  src/alphastrategy/web/static/js/core.js \
  src/alphastrategy/web/static/js/paint-strategies.js \
  src/alphastrategy/web/static/js/paint-run.js \
  src/alphastrategy/web/static/styles.css \
  src/alphastrategy/helptext.py README.md
git commit -m "feat: Roster names when a paper sleeve has no last weights"
```
