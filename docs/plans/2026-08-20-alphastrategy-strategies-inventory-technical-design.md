# Strategies Inventory Bands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the Strategies screen into Inventory, Import .asb, and Roster so lifecycle counts are first glance and the import gate is not the same job as the list.

**Architecture:** HTML bands + CSS `.metrics-4` + `js/paint-strategies.js` counts from existing `sleeveState`. Keep every import and table id. No API/Supervisor change. Do not revive `static/app.js`.

**Tech Stack:** Static HTML/CSS, cockpit JS parts, `helptext.py`, pytest string tests, e2e GET `/`.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-strategies-inventory-requirements.md`](../requirements/2026-08-20-alphastrategy-strategies-inventory-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- Import is not permission to trade. Start paper stays on Run.
- Cockpit JS is assembled from `web/static/js/` parts. Edit `js/paint-strategies.js`, not a file named `app.js`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `styles.css`, `js/paint-strategies.js`
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_web_tokens.py`
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_e2e_mocked.py`

**Interfaces:**
- Consumes: HTML/CSS/JS as served today (two generic Strategies panels)
- Produces: tests that fail until bands, `.metrics-4`, inventory painters, and help phrase exist

- [ ] **Step 1: Write the failing tests**

`tests/alphastrategy/test_web_tokens.py` (append):

```python
def test_html_strategies_inventory_bands(html_text: str) -> None:
    assert 'id="strat-inventory"' in html_text
    assert 'id="strat-import"' in html_text
    assert 'id="strat-roster"' in html_text
    assert '<h2 class="glance-heading">Inventory</h2>' in html_text
    assert '<h2 class="glance-heading">Import .asb</h2>' in html_text
    assert '<h2 class="glance-heading">Roster</h2>' in html_text
    strat = html_text[
        html_text.find('id="screen-strategies"') : html_text.find('id="screen-run"')
    ]
    inventory = strat[strat.find('id="strat-inventory"') : strat.find('id="strat-import"')]
    bring = strat[strat.find('id="strat-import"') : strat.find('id="strat-roster"')]
    roster = strat[strat.find('id="strat-roster"') :]
    assert 'id="strat-count-imported"' in inventory
    assert 'id="strat-count-paper"' in inventory
    assert 'id="strat-count-halted"' in inventory
    assert 'id="strat-count-stopped"' in inventory
    assert "hero" in inventory
    assert 'id="import-form"' in bring
    assert 'id="import-error"' in bring
    assert 'id="import-ok"' in bring
    assert 'id="strategies-table"' in roster
    assert 'id="import-form"' not in roster
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_css_strategies_inventory_bands(css_text: str) -> None:
    assert ".metrics-4" in css_text
    assert "repeat(4, minmax(0, 1fr))" in css_text


def test_js_paints_strategy_inventory(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderStrategies") : js_text.find("function runFormIsDirty")
    ]
    assert '"strat-count-paper"' in paint
    assert '"strat-count-imported"' in paint
    assert '"strat-count-halted"' in paint
    assert '"strat-count-stopped"' in paint
    assert '"status-running"' in paint
    assert '"status-halt"' in paint
    assert '"status-stopped"' in paint
    assert "classList.toggle(onClass" in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

`tests/alphastrategy/test_helptext.py` `REQUIRED_PHRASES` add `"Inventory / Import .asb / Roster"`.

`tests/alphastrategy/test_e2e_mocked.py` in `test_control_plane_serves_help` GET `/`:

```python
        assert 'id="strat-inventory"' in html
```

- [ ] **Step 2: Run — FAIL**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_strategies_inventory_bands tests/alphastrategy/test_web_tokens.py::test_css_strategies_inventory_bands tests/alphastrategy/test_web_tokens.py::test_js_paints_strategy_inventory tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_e2e_mocked.py::test_control_plane_serves_help -q
```

Expected: FAIL (`strat-inventory` missing, phrase missing).

- [ ] **Step 3: Commit tests**

```bash
git add tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_helptext.py tests/alphastrategy/test_e2e_mocked.py
git commit -m "test: require Strategies inventory glance bands"
```

---

### Task 2: Markup, CSS, painter, help

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`
- Modify: `src/alphastrategy/web/static/styles.css`
- Modify: `src/alphastrategy/web/static/js/paint-strategies.js`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `sleeveState` in `js/core.js` (unchanged four strings)
- Produces: three bands; counts painted every `renderStrategies` call including empty inventory

- [ ] **Step 4: HTML**

Replace `#screen-strategies` in `src/alphastrategy/web/static/index.html` with:

```html
    <section id="screen-strategies" class="screen" aria-label="Strategies">
      <div id="strat-inventory" class="glance-band">
        <h2 class="glance-heading">Inventory</h2>
        <div class="metrics metrics-4 nums">
          <div class="metric">
            <div class="metric-label">Imported</div>
            <div id="strat-count-imported" class="metric-value">—</div>
          </div>
          <div class="metric hero">
            <div class="metric-label">Paper</div>
            <div id="strat-count-paper" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Halted</div>
            <div id="strat-count-halted" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Stopped</div>
            <div id="strat-count-stopped" class="metric-value">—</div>
          </div>
        </div>
      </div>
      <div id="strat-import" class="glance-band">
        <h2 class="glance-heading">Import .asb</h2>
        <div class="panel">
          <form id="import-form">
            <input type="file" id="import-file" accept=".asb" required>
            <button type="submit" class="action primary">Upload .asb</button>
          </form>
          <div id="import-error" class="error-box hidden" role="alert">
            <div id="import-error-kind" class="error-kind"></div>
            <strong id="import-error-title"></strong>
            <div id="import-error-detail"></div>
            <div id="import-error-next" class="error-next"></div>
          </div>
          <div id="import-ok" class="ok-box hidden" role="status"></div>
        </div>
      </div>
      <div id="strat-roster" class="glance-band">
        <h2 class="glance-heading">Roster</h2>
        <div class="panel">
          <table id="strategies-table">
            <thead>
              <tr>
                <th>Bundle</th>
                <th>State</th>
                <th>Allocation</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </section>
```

- [ ] **Step 5: CSS**

In `src/alphastrategy/web/static/styles.css`, next to `.metrics-3` / `.metrics-2`:

```css
.metrics-4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
```

In the existing `@media (max-width: 639px)` block, include `.metrics-4`:

```css
@media (max-width: 639px) {
  .metrics-3,
  .metrics-4,
  .metrics-2 {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 6: Painter**

Replace `renderStrategies` in `src/alphastrategy/web/static/js/paint-strategies.js` with:

```javascript
  function renderStrategies() {
    const bundles = state.bundles || { imported: [], paper: {} };
    const risk = state.risk || { sleeves: {} };
    const tbody = document.querySelector("#strategies-table tbody");
    tbody.innerHTML = "";

    const ids = [...new Set([...bundles.imported, ...Object.keys(bundles.paper)])].sort();
    const counts = { imported: 0, paper: 0, halted: 0, stopped: 0 };
    for (const id of ids) {
      counts[sleeveState(id, bundles, state.status)] += 1;
    }
    const setCount = (elId, value, onClass) => {
      const el = document.getElementById(elId);
      if (!el) return;
      el.textContent = String(value);
      if (onClass) el.classList.toggle(onClass, value > 0);
    };
    setCount("strat-count-imported", counts.imported);
    setCount("strat-count-paper", counts.paper, "status-running");
    setCount("strat-count-halted", counts.halted, "status-halt");
    setCount("strat-count-stopped", counts.stopped, "status-stopped");

    if (!ids.length) {
      tbody.innerHTML = "<tr><td colspan='4' class='muted'>No bundles imported</td></tr>";
    } else {
      for (const id of ids) {
        const st = sleeveState(id, bundles, state.status);
        const alloc = bundles.paper[id] || 0;
        const policy = risk.sleeves[id];
        const statusClass =
          st === "paper" ? "running" : st === "halted" ? "halt" : st === "stopped" ? "stopped" : "muted";
        const tr = document.createElement("tr");
        tr.innerHTML = `
        <td>${id}</td>
        <td class="status-${statusClass}">${st}</td>
        <td class="nums">${fmtPct(alloc)}</td>
        <td class="muted">${riskSummary(policy)}</td>
      `;
        tbody.appendChild(tr);
      }
    }

    const select = document.getElementById("start-bundle");
    const prev = select.value;
    select.innerHTML = "";
    for (const id of bundles.imported) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = id;
      select.appendChild(opt);
    }
    if (prev && bundles.imported.includes(prev)) {
      select.value = prev;
    }
  }
```

Keep the file as an IIFE fragment (leading two-space indent, no extra wrapper). The next concatenated function is `runFormIsDirty` in `js/paint-run.js`; the JS slice test uses that boundary.

- [ ] **Step 7: Help + README**

`how_strategies` body:

```python
            "Three bands: Inventory / Import .asb / Roster. Paper is the hero count. "
            "The four tiles are imported, paper, halted, and stopped. "
            "Upload a qualified .asb. Import is not permission to trade. "
            "Failures name the gate (hash, schema, conformance) and a next action. "
            "Start paper on Run."
```

In `SECTIONS` cockpit body, after the Portfolio bands sentence, add:

```text
Strategies is three bands Inventory / Import .asb / Roster. Paper is the hero count.
```

README Quiet cockpit, after the Portfolio paragraph, add:

```text
Strategies is three bands: **Inventory** (Imported / Paper / Halted / Stopped;
Paper is the hero), **Import .asb**, and **Roster**. Import is not permission
to trade; start paper on Run.
```

- [ ] **Step 8: Run tests — PASS**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

Expected: all pass. No real broker.

- [ ] **Step 9: Commit**

```bash
git add src/alphastrategy/web/static/index.html src/alphastrategy/web/static/styles.css src/alphastrategy/web/static/js/paint-strategies.js src/alphastrategy/helptext.py README.md
git commit -m "feat: give Strategies inventory, import, and roster bands"
```

---

## Spec coverage

| Spec section | Task |
| --- | --- |
| Three bands + order | 2 HTML |
| Inventory tiles / hero / colors | 2 HTML + painter |
| `.metrics-4` | 2 CSS |
| Keep import ids | 2 HTML |
| Counts from `sleeveState`, empty paints 0 | 2 painter |
| Help / README | 2 copy |
| Verification / e2e | 1 tests |

## Placeholder scan

None. Exact ids, CSS, painter, help strings, and commands.
