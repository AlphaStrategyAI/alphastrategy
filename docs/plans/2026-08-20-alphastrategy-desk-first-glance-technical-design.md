# Desk First Glance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (this cycle explicitly chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the empty Quiet cockpit teach import → paper start, and make Wanted/Got plus Gross-vs-cap glanceable without a sixth screen or demo fills.

**Architecture:** All behavior is static HTML/CSS/JS plus help copy. `#first-run` lives in chrome next to `#desk-banners`. Bars are CSS. Risk reads `state.bundles.paper`. No Supervisor change.

**Tech Stack:** Existing Quiet cockpit, pytest string tests, mocked e2e GET `/`.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-desk-first-glance-requirements.md`](../requirements/2026-08-20-alphastrategy-desk-first-glance-requirements.md)

## Global Constraints

- Package `alphastrategy`, paper-only walls unchanged.
- Do not grow `src/openstrategy/`.
- Five `#nav` screens. No `window.confirm`. Locked color tokens only.
- No chart library. No ghost positions.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never place a real order.

## File map

- Modify: `src/alphastrategy/web/static/index.html` — `#first-run`, Book column, gross bar mount
- Modify: `src/alphastrategy/web/static/styles.css` — `.first-run`, `.wg-track`, `.util-track`
- Modify: `src/alphastrategy/web/static/app.js` — renderFirstRun, wantedGotBar, util fill, empty copy, Risk allocation, data-go-screen
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`
- Test: `tests/alphastrategy/test_helptext.py`
- Test: `tests/alphastrategy/test_e2e_mocked.py`

---

### Task 1: Static HTML/CSS mounts and token tests

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`
- Modify: `src/alphastrategy/web/static/styles.css`
- Test: `tests/alphastrategy/test_web_tokens.py`

**Interfaces:**
- Produces: `#first-run`, `#metric-gross-bar`, Book `<th>`, `.wg-track`, `.util-track`, `.first-run`

- [ ] **Step 1: Write the failing tests**

Append to `tests/alphastrategy/test_web_tokens.py`:

```python
def test_html_first_run_and_book_column(html_text: str) -> None:
    assert 'id="first-run"' in html_text
    first_at = html_text.find('id="first-run"')
    portfolio_at = html_text.find('id="screen-portfolio"')
    assert 0 <= first_at < portfolio_at
    assert "Start this paper desk" in html_text
    assert "Import is not permission to trade" in html_text
    assert 'data-go-screen="strategies"' in html_text
    assert 'data-go-screen="run"' in html_text
    assert ">Book<" in html_text
    assert 'id="metric-gross-bar"' in html_text


def test_css_first_glance_tracks_use_locked_tokens(css_text: str) -> None:
    assert ".first-run" in css_text
    assert ".wg-track" in css_text
    assert ".util-track" in css_text
    assert ".wg-wanted" in css_text
    first = re.search(r"\.first-run\s*\{[^}]*\}", css_text)
    assert first is not None
    assert "#10b981" in first.group(0).lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_first_run_and_book_column tests/alphastrategy/test_web_tokens.py::test_css_first_glance_tracks_use_locked_tokens -q`

Expected: FAIL — missing `#first-run` / `.wg-track`.

- [ ] **Step 3: Write minimal HTML/CSS**

In `index.html`, immediately after `</div>` of `#desk-banners` and before `#screen-portfolio`:

```html
    <div id="first-run" class="panel first-run hidden" role="status">
      <h2>Start this paper desk</h2>
      <p>Import a qualified .asb, then start a paper sleeve. Import is not permission to trade.</p>
      <button type="button" class="action primary" data-go-screen="strategies">Import .asb</button>
      <button type="button" class="action" data-go-screen="run">Open Run</button>
    </div>
```

In the Gross metric, after `#metric-gross`:

```html
          <div id="metric-gross-bar" class="util-track hidden" aria-hidden="true"></div>
```

In positions `<thead>`:

```html
              <tr><th>Symbol</th><th>Qty</th><th>Notional</th><th>Wanted</th><th>Got</th><th>Book</th></tr>
```

Append to `styles.css`:

```css
.first-run {
  border-color: #10b981;
  margin-bottom: 0.75rem;
}

.first-run p {
  color: #9ba3b4;
  font-size: 0.85rem;
  margin: 0 0 0.65rem;
}

.wg-track,
.util-track {
  position: relative;
  height: 8px;
  background: #0b0e14;
  border: 1px solid #2a3142;
  border-radius: 3px;
  overflow: hidden;
}

.util-track {
  margin-top: 0.35rem;
}

.wg-got,
.util-fill {
  display: block;
  height: 100%;
  background: #10b981;
}

.wg-track.drift .wg-got,
.util-track.warn .util-fill {
  background: #f59e0b;
}

.util-track.fail .util-fill {
  background: #ef4444;
}

.wg-wanted {
  position: absolute;
  top: 0;
  width: 2px;
  height: 100%;
  background: #e5e9f0;
  transform: translateX(-1px);
}

.wg-cell {
  min-width: 88px;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_first_run_and_book_column tests/alphastrategy/test_web_tokens.py::test_css_first_glance_tracks_use_locked_tokens tests/alphastrategy/test_web_tokens.py::test_html_nav_labels_exact_set tests/alphastrategy/test_web_tokens.py::test_css_contains_locked_tokens -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/web/static/index.html src/alphastrategy/web/static/styles.css tests/alphastrategy/test_web_tokens.py
git commit -m "feat: first-run chrome and Book/gross track mounts"
```

---

### Task 2: JS render — first-run, bars, empty copy, Risk allocation

**Files:**
- Modify: `src/alphastrategy/web/static/app.js`
- Test: `tests/alphastrategy/test_web_tokens.py`

**Interfaces:**
- Consumes: `state.bundles`, `state.risk.account.max_gross`, `state.risk.account.max_name_weight`, position `wanted`/`weight`
- Produces: `renderFirstRun`, `wantedGotBar`, `renderGrossUtilization`, `data-go-screen` click → `showScreen`

- [ ] **Step 1: Write the failing tests**

```python
def test_js_first_glance_behaviors(js_text: str) -> None:
    assert "function renderFirstRun" in js_text
    assert "function wantedGotBar" in js_text
    assert "function renderGrossUtilization" in js_text
    assert "data-go-screen" in js_text
    assert "No positions yet. Import a .asb to begin." in js_text
    assert "Imported bundles are not trading. Start paper on Run." in js_text
    assert "The next legal open or close rebalance will trade." in js_text
    assert "wg-track" in js_text
    assert "util-fill" in js_text
    assert "Allocation " in js_text
    assert "window.confirm" not in js_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_first_glance_behaviors -q`

Expected: FAIL — `renderFirstRun` missing.

- [ ] **Step 3: Write minimal JS**

Add helpers after `riskSummary`:

```javascript
  function importedIds() {
    const bundles = state.bundles || { imported: [], paper: {} };
    const paper = bundles.paper || {};
    return [...new Set([...(bundles.imported || []), ...Object.keys(paper)])];
  }

  function hasPaperSleeve() {
    const paper = (state.bundles && state.bundles.paper) || {};
    return Object.keys(paper).some((id) => Number(paper[id]) > 0);
  }

  function renderFirstRun() {
    const el = document.getElementById("first-run");
    if (!el) return;
    const empty = importedIds().length === 0;
    el.classList.toggle("hidden", !empty);
  }

  function wantedGotBar(wanted, got, cap) {
    const w = Math.max(0, Number(wanted) || 0);
    const g = Math.max(0, Number(got) || 0);
    const scale = Math.max(Number(cap) || 0.2, w, g, 0.01);
    const wPct = Math.min(100, (w / scale) * 100);
    const gPct = Math.min(100, (g / scale) * 100);
    const drift = Math.abs(w - g) > 0.001 ? " drift" : "";
    return (
      `<div class="wg-cell"><div class="wg-track${drift}" aria-label="wanted ${fmtPct(w)} got ${fmtPct(g)}">` +
      `<span class="wg-got" style="width:${gPct}%"></span>` +
      `<span class="wg-wanted" style="left:${wPct}%"></span>` +
      `</div></div>`
    );
  }

  function renderGrossUtilization(gross) {
    const bar = document.getElementById("metric-gross-bar");
    if (!bar) return;
    const cap = Number(state.risk && state.risk.account && state.risk.account.max_gross);
    const limit = cap > 0 ? cap : 1;
    const ratio = limit ? gross / limit : 0;
    const pct = Math.min(100, Math.max(0, ratio * 100));
    bar.classList.remove("hidden", "warn", "fail");
    if (ratio >= 1) bar.classList.add("fail");
    else if (ratio >= 0.9) bar.classList.add("warn");
    bar.innerHTML = `<span class="util-fill" style="width:${pct}%"></span>`;
    bar.setAttribute("aria-label", `gross ${fmtPct(gross)} of cap ${fmtPct(limit)}`);
  }
```

In `renderPortfolio`, after setting Gross text:

```javascript
    const gross = grossExposure(portfolio);
    document.getElementById("metric-gross").textContent = fmtPct(gross);
    renderGrossUtilization(gross);
    renderFirstRun();
```

(Replace the existing Gross `textContent` line so Gross is not written twice.)

Empty positions: `colspan='6'` and the three phrases using `importedIds()` / `hasPaperSleeve()`.

Position rows: append Book cell:

```javascript
        const cap =
          (state.risk && state.risk.account && state.risk.account.max_name_weight) || 0.2;
        tr.innerHTML =
          `<td>${pos.symbol || "—"}</td><td class="nums">${fmtNum(pos.qty, 4)}</td>` +
          `<td class="nums">${notional}</td><td class="nums">${wanted}</td>` +
          `<td class="nums">${got}</td><td>${wantedGotBar(pos.wanted, pos.weight, cap)}</td>`;
```

In `renderRisk`, sleeve heading:

```javascript
      const alloc = ((state.bundles && state.bundles.paper) || {})[id] || 0;
      panel.innerHTML = `<h2>${id}</h2><p class="muted nums">Allocation ${fmtPct(alloc)}</p>`;
```

At the bottom with other listeners:

```javascript
  document.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-go-screen]");
    if (!btn) return;
    showScreen(btn.getAttribute("data-go-screen"));
  });
```

Call `renderFirstRun()` from `refresh()` after `renderPortfolio` as well (already inside renderPortfolio).

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/web/static/app.js tests/alphastrategy/test_web_tokens.py
git commit -m "feat: glanceable wanted/got, gross util, and first-run actions"
```

---

### Task 3: Help, README, e2e GET /

**Files:**
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`
- Test: `tests/alphastrategy/test_helptext.py`
- Test: `tests/alphastrategy/test_e2e_mocked.py`

- [ ] **Step 1: Write the failing tests**

Add `"Start this paper desk"` to `REQUIRED_PHRASES` in `test_helptext.py` (lowercase match).

In `test_e2e_isolated_sleeve_kill` or the GET `/` assertion near `desk-banners`, also assert `id="first-run"`. The isolated-kill test already does `conn.request("GET", "/")` and checks `desk-banners`. Add `assert 'id="first-run"' in html` there.

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

Expected: FAIL — phrase missing from helptext.

- [ ] **Step 3: Write copy**

`helptext.py` cockpit body, after Wanted/Got sentence:

```text
 An empty desk says Start this paper desk and tells you to import, then start paper.
 Portfolio Book is wanted versus got. Gross utilization is against the account cap.
 Risk lists each sleeve allocation as text.
```

README Quiet cockpit, after Portfolio sentence:

```markdown
An empty desk shows **Start this paper desk** (import, then start paper).
Positions include a **Book** bar (wanted vs got). Gross shows utilization
against the account cap. Risk lists sleeve allocation as text.
```

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_e2e_mocked.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/helptext.py README.md tests/alphastrategy/test_helptext.py tests/alphastrategy/test_e2e_mocked.py
git commit -m "docs: empty desk, Book bar, and gross utilization"
```

---

### Task 4: Full suite

- [ ] **Step 1:** `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass.

- [ ] **Step 2:** Commit only if fixes were needed.

---

## Self-review

| Spec item | Task |
| --- | --- |
| `#first-run` outside screens, locked copy, data-go-screen | 1–2 |
| Three empty-position strings | 2 |
| Book bar + drift | 2 |
| Gross util 90/100 | 2 |
| Risk allocation text | 2 |
| Help/README/e2e | 3 |
| No sixth screen, no window.confirm, locked tokens | 1–2 tests |
| No demo fills / no Supervisor math change | file map |
