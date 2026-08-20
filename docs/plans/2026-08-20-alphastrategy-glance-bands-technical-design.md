# Portfolio Glance Bands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Group Portfolio metrics into Book, Flatten budgets, and Clock bands with a hero Equity, and put Positions beside Sleeves on a wide desk.

**Architecture:** HTML structure + CSS only. Keep every metric id. No API/Supervisor change. Replace inline margins with `.stack`.

**Tech Stack:** Static HTML/CSS, pytest string tests, e2e GET `/`.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-glance-bands-requirements.md`](../requirements/2026-08-20-alphastrategy-glance-bands-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `styles.css`
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests for mounts

- [ ] **Step 1:** Add to `test_web_tokens.py`:

```python
def test_html_glance_bands(html_text: str) -> None:
    assert 'id="glance-book"' in html_text
    assert 'id="glance-risk"' in html_text
    assert 'id="glance-clock"' in html_text
    assert ">Book<" in html_text
    assert "Flatten budgets" in html_text
    assert ">Clock<" in html_text
    book = html_text[html_text.find('id="glance-book"'):html_text.find('id="glance-risk"')]
    risk = html_text[html_text.find('id="glance-risk"'):html_text.find('id="glance-clock"')]
    clock = html_text[html_text.find('id="glance-clock"'):html_text.find('id="clock-line"')]
    assert 'id="metric-equity"' in book
    assert 'id="metric-cash"' in book
    assert 'id="metric-pnl"' in book
    assert 'id="metric-gross"' in risk
    assert 'id="metric-names"' in risk
    assert 'id="metric-orders"' in risk
    assert 'id="metric-session"' in clock
    assert 'id="metric-countdown"' in clock
    assert "hero" in book
    assert 'style="margin-top' not in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_css_glance_bands(css_text: str) -> None:
    assert ".glance-band" in css_text
    assert ".glance-heading" in css_text
    assert ".book-grid" in css_text
    assert ".stack" in css_text
    assert "1.85rem" in css_text
```

e2e GET `/`: `id="glance-book"`.

Help: add `"Flatten budgets"` to `REQUIRED_PHRASES`.

- [ ] **Step 2:** Run — FAIL.

- [ ] **Step 3:** Implement HTML/CSS as specified. Book metrics: Equity gets `class="metric hero"`. `.metrics-book` / `.metrics-risk` / `.metrics-clock` or `.glance-band .metrics` with nth — prefer extra classes `metrics-3` and `metrics-2`.

```css
.glance-heading {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #9ba3b4;
  margin: 0 0 0.4rem;
}
.glance-band + .glance-band {
  margin-top: 0.85rem;
}
.metrics-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.metrics-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
@media (max-width: 639px) {
  .metrics-3,
  .metrics-2 {
    grid-template-columns: 1fr;
  }
}
.metric.hero .metric-value {
  font-size: 1.85rem;
}
.stack { margin-top: 0.75rem; }
@media (min-width: 800px) {
  .book-grid {
    grid-template-columns: 1fr 1fr;
  }
}
```

Keep `.metrics { display:grid; gap }` so 3/2 classes only override columns.

- [ ] **Step 4:** Tests PASS.

---

### Task 2: Help / README

Cockpit: Portfolio is three bands Book, Flatten budgets, Clock; Equity is the hero; Positions and Sleeves sit side by side on a wide desk.

Full suite green.

## Spec coverage

| Requirement | Task |
| --- | --- |
| three bands + hero + columns | 1 |
| book-grid + stack | 1 |
| help/README | 2 |
| ids unchanged | no app.js painter rewrite |
