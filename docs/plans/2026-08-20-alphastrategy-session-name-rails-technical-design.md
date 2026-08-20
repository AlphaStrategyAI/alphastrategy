# Session Clock and Name Rails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make session, next rebalance, name-vs-cap, and spoken allocation glanceable on Portfolio, and stop `renderBanners` from throwing.

**Architecture:** Static Quiet cockpit only. Reuse `.util-track`. No Supervisor change.

**Tech Stack:** HTML/CSS/JS, pytest string tests, e2e GET `/`.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-session-name-rails-requirements.md`](../requirements/2026-08-20-alphastrategy-session-name-rails-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `styles.css`, `app.js`
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Banner killReason + HTML/CSS mounts

**Files:** `app.js` (killReason only after its failing test), `index.html`, `styles.css`, `test_web_tokens.py`

- [ ] **Step 1: Failing tests**

```python
def test_js_render_banners_declares_reason_once(js_text: str) -> None:
    block = js_text.split("function renderBanners")[1].split("function renderPortfolio")[0]
    assert block.count("const reason") == 1
    assert "killReason" in block


def test_html_session_and_cap_mounts(html_text: str) -> None:
    assert 'id="metric-session"' in html_text
    assert 'id="metric-countdown"' in html_text
    assert 'id="metric-countdown-kind"' in html_text
    assert 'id="sleeve-alloc-track"' in html_text
    assert ">Cap<" in html_text
    portfolio_at = html_text.find('id="screen-portfolio"')
    assert html_text.find('id="metric-session"') > portfolio_at


def test_css_focus_visible_and_metric_sub(css_text: str) -> None:
    assert ":focus-visible" in css_text
    assert ".metric-sub" in css_text
```

- [ ] **Step 2:** Run those three tests — FAIL (duplicate `const reason`, missing mounts).

- [ ] **Step 3: Implementation**

In `renderBanners`, `const killReason = lastKill && lastKill.reason;` and branch on `killReason`.

HTML: after Gross metric, two cards:

```html
        <div class="metric">
          <div class="metric-label">Session</div>
          <div id="metric-session" class="metric-value">—</div>
        </div>
        <div class="metric">
          <div class="metric-label">Next rebalance</div>
          <div id="metric-countdown" class="metric-value">—</div>
          <div id="metric-countdown-kind" class="metric-sub">—</div>
        </div>
```

Positions head: add `<th>Cap</th>` after Book.

Sleeves panel:

```html
          <h2>Sleeves</h2>
          <p id="sleeve-alloc-label" class="muted hidden"></p>
          <div id="sleeve-alloc-track" class="util-track hidden" aria-hidden="true"></div>
```

CSS append:

```css
.metric-sub {
  font-size: 0.72rem;
  color: #9ba3b4;
  margin-top: 0.15rem;
  text-transform: lowercase;
}

nav button:focus-visible,
button.action:focus-visible,
#help-toggle:focus-visible {
  outline: 2px solid #9ba3b4;
  outline-offset: 2px;
}

#metric-session.open {
  color: #10b981;
}
```

- [ ] **Step 4:** Re-run the three tests — PASS (`test_html`/`test_css` pass; `killReason` test passes after JS rename).

If HTML tests pass before JS rename, that is expected. `test_js_render_banners_declares_reason_once` must fail until the rename.

- [ ] **Step 5:** Commit `fix: unique halt reason in banners; session/cap mounts`

Do the rename in this task so the banners test is green before Task 2.

---

### Task 2: JS renderSessionMetrics, nameCapBar, renderSleeveAllocBook

**Files:** `app.js`, `test_web_tokens.py`

- [ ] **Step 1: Failing test**

```python
def test_js_session_name_and_alloc_rails(js_text: str) -> None:
    assert "function renderSessionMetrics" in js_text
    assert "function nameCapBar" in js_text
    assert "function renderSleeveAllocBook" in js_text
    assert "Spoken " in js_text
    assert "colspan='7'" in js_text
    assert "window.confirm" not in js_text
```

- [ ] **Step 2:** Run — FAIL.

- [ ] **Step 3: JS**

Add:

```javascript
  function renderSessionMetrics() {
    const sessionEl = document.getElementById("metric-session");
    const countEl = document.getElementById("metric-countdown");
    const kindEl = document.getElementById("metric-countdown-kind");
    const clockLine = document.getElementById("clock-line");
    const clock = state.status && state.status.clock;
    const countdown = state.status && state.status.countdown;
    sessionEl.classList.remove("open");
    if (!clock || clock.error) {
      sessionEl.textContent = "UNAVAILABLE";
      countEl.textContent = "—";
      kindEl.textContent = "—";
      clockLine.textContent = "Clock unavailable";
      return;
    }
    if (clock.is_open) {
      sessionEl.textContent = "OPEN";
      sessionEl.classList.add("open");
    } else {
      sessionEl.textContent = "CLOSED";
    }
    if (countdown) {
      countEl.textContent = fmtCountdown(countdown.seconds);
      kindEl.textContent = countdown.next_rebalance || "—";
    } else {
      countEl.textContent = "—";
      kindEl.textContent = "—";
    }
    clockLine.textContent = `now ${clock.timestamp || "—"}`;
  }

  function nameCapBar(got, cap) {
    const g = Math.max(0, Number(got) || 0);
    const limit = Number(cap) > 0 ? Number(cap) : 0.2;
    const ratio = g / limit;
    const pct = Math.min(100, Math.max(0, ratio * 100));
    let cls = "util-track";
    if (ratio >= 1) cls += " fail";
    else if (ratio >= 0.9) cls += " warn";
    return (
      `<div class="wg-cell"><div class="${cls}" aria-label="name ${fmtPct(g)} of cap ${fmtPct(limit)}">` +
      `<span class="util-fill" style="width:${pct}%"></span></div></div>`
    );
  }

  function renderSleeveAllocBook(sleeves) {
    const track = document.getElementById("sleeve-alloc-track");
    const label = document.getElementById("sleeve-alloc-label");
    const ids = Object.keys(sleeves || {});
    if (!track || !label) return;
    if (!ids.length) {
      track.classList.add("hidden");
      label.classList.add("hidden");
      track.innerHTML = "";
      return;
    }
    const spoken = ids.reduce((sum, id) => sum + (Number(sleeves[id]) || 0), 0);
    const pct = Math.min(100, Math.max(0, spoken * 100));
    track.classList.remove("hidden", "warn", "fail");
    label.classList.remove("hidden");
    if (spoken >= 1) track.classList.add("fail");
    else if (spoken >= 0.9) track.classList.add("warn");
    track.innerHTML = `<span class="util-fill" style="width:${pct}%"></span>`;
    track.removeAttribute("aria-hidden");
    track.setAttribute("aria-label", `spoken ${fmtPct(spoken)} of paper book`);
    label.textContent = `Spoken ${fmtPct(spoken)} of paper book`;
  }
```

Call `renderSessionMetrics()` from `renderPortfolio` **instead of** the old clock-line OPEN/CLOSED/countdown block.

Position rows: `colspan='7'` on empty; append `<td>${nameCapBar(pos.weight, cap)}</td>`.

After sleeves table fill: `renderSleeveAllocBook(sleeves)`.

- [ ] **Step 4:** `pytest tests/alphastrategy/test_web_tokens.py -q` — PASS.

- [ ] **Step 5:** Commit `feat: session tiles, name cap rails, spoken allocation`

---

### Task 3: Help, README, e2e

Add `"Next rebalance"` to `REQUIRED_PHRASES` (exact, like Wanted). Cockpit help: session/countdown tiles, Cap vs single-name limit, spoken paper book.

E2E GET `/` assert `id="metric-countdown"`.

README Quiet cockpit: one sentence on session tiles and Cap.

- [ ] Full suite `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

---

## Self-review

Session tiles, Cap rail, spoken allocation, killReason, focus-visible, help — tasked. No TBD. Isolation math untouched.
