# Positions Book names Next against Wanted Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Positions glance Wanted hero and the Book bar name Next against last Wanted so the home book matches the Next column / Caps send without a fifth tile.

**Architecture:** Cockpit-only. `paintPositionsWantedNextSub` counts finite Next that differs from Wanted. `wantedGotBar` draws a third `.wg-next` mark under the white Wanted tick. No API change.

**Tech Stack:** Python 3.9+, pytest, cockpit HTML/CSS/JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-next-glance-requirements.md`](../requirements/2026-08-21-alphastrategy-next-glance-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET. Do not place.
- Wanted stays last combined. Book Drift stays last wanted vs last fill.
- Positions glance stays Rows / Wanted / Got / At cap. No fifth tile.
- Keep `Next rebalance`. Keep Cash composition labels. Keep `colspan='9'`. Keep `formatNextCell`.
- `paint-portfolio.js` and `paint-rails.js` stay ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_e2e_mocked.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_web_tokens.py`
- Modify: `tests/alphastrategy/test_e2e_mocked.py`

**Interfaces:**
- Consumes: existing `next` on portfolio positions; `formatNextCell`; four glance tiles
- Produces: locked HTML id `pos-count-wanted-sub`; JS `paintPositionsWantedNextSub` / `wg-next`; help phrase `Positions Book names Next against Wanted`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add after `Positions Next follows current allocations on last sleeve weights`:

```python
    "Positions Book names Next against Wanted",
```

In `test_html_positions_glance_bands`, after `id="pos-count-wanted"`, assert `id="pos-count-wanted-sub"` in `pos`. Keep `metrics-4`. Keep Wanted < Next < Got.

In `test_js_paints_positions_glance_tiles`, after `pos-count-wanted`, assert `paintPositionsWantedNextSub`.

In `test_e2e_mocked.py` `test_control_plane_serves_help`, after `id="pos-count-wanted"`, assert `id="pos-count-wanted-sub"`.

After `test_css_positions_next_warn_token`:

```python
def test_html_positions_wanted_next_sub(html_text: str) -> None:
    port = html_text[
        html_text.find('id="screen-portfolio"') : html_text.find('id="screen-strategies"')
    ]
    pos = port[port.find('id="glance-positions"') : port.find('id="glance-sleeves"')]
    wanted = pos[pos.find('id="pos-count-wanted"') :]
    assert 'id="pos-count-wanted-sub"' in wanted
    assert "metrics-4" in pos
    assert wanted.find('id="pos-count-wanted"') < wanted.find('id="pos-count-wanted-sub"')
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_paints_positions_wanted_next_sub(js_text: str) -> None:
    assert "function paintPositionsWantedNextSub" in js_text
    helper = js_text[
        js_text.find("function paintPositionsWantedNextSub") : js_text.find(
            "function paintUtilTrack"
        )
    ]
    assert "pos-count-wanted-sub" in helper
    assert '"next "' in helper
    assert 'classList.toggle("warn"' in helper
    glance = js_text[
        js_text.find("function renderPositionsGlance") : js_text.find("function renderDeskPulse")
    ]
    assert "paintPositionsWantedNextSub(" in glance
    assert "Gross cap" not in js_text
    assert "Order size" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_wanted_got_bar_names_next(js_text: str) -> None:
    rails = js_text[
        js_text.find("function wantedGotBar") : js_text.find("function paintUtilTrack")
    ]
    assert "wg-next" in rails
    assert "fill" in rails
    port = js_text[
        js_text.find("function renderPortfolio") : js_text.find("function pulseLabel")
    ]
    assert "wantedGotBar(pos.wanted, pos.weight, cap, pos.fill, pos.next)" in port
    assert "colspan='9'" in port
    assert "Gross cap" not in js_text
    assert "Order size" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_positions_book_next_warn_token(css_text: str) -> None:
    sub = re.search(r"#pos-count-wanted-sub\.warn\s*\{[^}]*\}", css_text)
    mark = re.search(r"\.wg-next\s*\{[^}]*\}", css_text)
    assert sub is not None and "#f59e0b" in sub.group(0).lower()
    assert mark is not None and "#f59e0b" in mark.group(0).lower()
```

Keep `test_js_paints_positions_next`. Keep `test_js_book_drift_uses_fill_not_mark`. Keep `test_js_paints_positions_glance_tiles` four tile ids.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_html_positions_glance_bands tests/alphastrategy/test_web_tokens.py::test_html_positions_wanted_next_sub tests/alphastrategy/test_web_tokens.py::test_js_paints_positions_wanted_next_sub tests/alphastrategy/test_web_tokens.py::test_js_wanted_got_bar_names_next tests/alphastrategy/test_web_tokens.py::test_css_positions_book_next_warn_token tests/alphastrategy/test_web_tokens.py::test_js_paints_positions_next tests/alphastrategy/test_web_tokens.py::test_js_book_drift_uses_fill_not_mark tests/alphastrategy/test_e2e_mocked.py::test_control_plane_serves_help -q
```

Expected: new HTML/JS/CSS/help tests fail (no sub id / no `wg-next` / phrase missing). Positions Next column and fill-drift locks still pass.

- [ ] **Step 3: Commit tests and docs**

```bash
git add docs/requirements/2026-08-21-alphastrategy-next-glance-requirements.md docs/plans/2026-08-21-alphastrategy-next-glance-technical-design.md tests/alphastrategy/test_helptext.py tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_e2e_mocked.py
git commit -m "test: Positions Book names Next against Wanted"
```

---

### Task 2: Implement

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`
- Modify: `src/alphastrategy/web/static/styles.css`
- Modify: `src/alphastrategy/web/static/js/paint-rails.js`
- Modify: `src/alphastrategy/web/static/js/paint-portfolio.js`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `pos.next` already on GET `/api/portfolio`
- Produces: `#pos-count-wanted-sub`; `paintPositionsWantedNextSub(positions)`; `wantedGotBar(..., next)`

- [ ] **Step 4: HTML and CSS**

Wanted hero in `index.html`:

```html
            <div class="metric hero">
              <div class="metric-label">Wanted</div>
              <div id="pos-count-wanted" class="metric-value">—</div>
              <div id="pos-count-wanted-sub" class="metric-sub">—</div>
            </div>
```

`styles.css` after `#pos-count-cap.fail`:

```css
#pos-count-wanted-sub.warn {
  color: #f59e0b;
}
```

After `.wg-wanted`:

```css
.wg-next {
  position: absolute;
  top: 0;
  width: 2px;
  height: 100%;
  background: #f59e0b;
  transform: translateX(-1px);
}
```

- [ ] **Step 5: JS**

Replace `wantedGotBar` in `paint-rails.js` with:

```javascript
  function wantedGotBar(wanted, got, cap, fill, next) {
    const w = Math.max(0, Number(wanted) || 0);
    const g = Math.max(0, Number(got) || 0);
    const rawN = Number(next);
    const hasNext = next != null && next !== "" && Number.isFinite(rawN);
    const n = hasNext ? Math.max(0, rawN) : 0;
    const capN = finiteNumber(cap, 0.2);
    const scale = Math.max(capN, w, g, n, 0.01);
    const fillW =
      fill == null || fill === undefined ? g : Math.max(0, Number(fill) || 0);
    const drift = Math.abs(w - fillW) > 0.001 ? " drift" : "";
    const nextMark = hasNext
      ? `<span class="wg-next" style="left:${Math.min(100, (n / scale) * 100)}%"></span>`
      : "";
    return (
      `<div class="wg-cell"><div class="wg-track${drift}" aria-label="wanted ${fmtPct(w)} got ${fmtPct(g)}` +
      (hasNext ? ` next ${fmtPct(n)}` : "") +
      `">` +
      `<span class="wg-got" style="width:${Math.min(100, (g / scale) * 100)}%"></span>` +
      nextMark +
      `<span class="wg-wanted" style="left:${Math.min(100, (w / scale) * 100)}%"></span>` +
      `</div></div>`
    );
  }

  function paintPositionsWantedNextSub(positions) {
    const sub = document.getElementById("pos-count-wanted-sub");
    if (!sub) return;
    let diffs = 0;
    let named = 0;
    for (const pos of positions || []) {
      const nxt = Number(pos.next);
      if (pos.next == null || pos.next === "" || !Number.isFinite(nxt)) continue;
      named += 1;
      const w = Number(pos.wanted);
      if (
        pos.wanted == null ||
        pos.wanted === "" ||
        !Number.isFinite(w) ||
        Math.abs(nxt - w) > 1e-9
      ) {
        diffs += 1;
      }
    }
    const show = named > 0 && diffs > 0;
    sub.textContent = show ? "next " + diffs : "—";
    sub.classList.toggle("warn", show);
  }
```

Keep `paintPositionsWantedNextSub` **before** `paintUtilTrack` so the wantedGotBar→paintUtilTrack slice still contains `wg-next` and the new helper. File ≤ 400 lines.

`paint-portfolio.js` `renderPositionsGlance`: after `if (wantedEl) wantedEl.textContent = String(wantedN);` add `paintPositionsWantedNextSub(rows);`.

Call site: `wantedGotBar(pos.wanted, pos.weight, cap, pos.fill, pos.next)`. File ≤ 400 lines.

- [ ] **Step 6: Help and README**

`helptext.py`: add `Positions Book names Next against Wanted. ` to `cockpit` (after Positions Book column), `how_portfolio` (after Positions Next follows current allocations), `task_wanted` (after Positions Next follows current allocations).

README Portfolio: after the Book bar (wanted vs got), same sentence. Keep `Next rebalance`. Keep `Rows / Wanted / Got / At cap`. Keep `Positions Next follows current allocations on last sleeve weights`.

- [ ] **Step 7: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

Expected: all pass. Confirm `js/paint-rails.js` and `js/paint-portfolio.js` each have ≤ 400 newlines.

- [ ] **Step 8: Commit, push, update PR**

```bash
git add src/alphastrategy/web/static/index.html src/alphastrategy/web/static/styles.css src/alphastrategy/web/static/js/paint-rails.js src/alphastrategy/web/static/js/paint-portfolio.js src/alphastrategy/helptext.py README.md
git commit -m "feat: Positions Book names Next against Wanted"
```
