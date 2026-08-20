# Run Kill-Switch Zones Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the Run screen into Start paper, Sleeves, After halt, and Flatten account so resume is not in the same panel as account flatten.

**Architecture:** HTML structure + CSS + help copy. Keep every control id. No API/Supervisor/`app.js` painter rewrite.

**Tech Stack:** Static HTML/CSS, `helptext.py`, pytest string tests, e2e GET `/`.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-run-zones-requirements.md`](../requirements/2026-08-20-alphastrategy-run-zones-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- Account kill still requires checkbox + `FLATTEN`. Resume stays one click.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `styles.css`
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests + markup

- [ ] **Step 1: Write the failing tests**

`tests/alphastrategy/test_web_tokens.py`:

```python
def test_html_run_kill_switch_zones(html_text: str) -> None:
    assert 'id="run-promote"' in html_text
    assert 'id="run-book"' in html_text
    assert 'id="run-recover"' in html_text
    assert 'id="run-flatten"' in html_text
    assert '<h2 class="glance-heading">Start paper</h2>' in html_text
    assert '<h2 class="glance-heading">Sleeves</h2>' in html_text
    assert '<h2 class="glance-heading">After halt</h2>' in html_text
    assert '<h2 class="glance-heading">Flatten account</h2>' in html_text
    run = html_text[html_text.find('id="screen-run"') : html_text.find('id="screen-activity"')]
    promote = run[run.find('id="run-promote"') : run.find('id="run-book"')]
    book = run[run.find('id="run-book"') : run.find('id="run-recover"')]
    recover = run[run.find('id="run-recover"') : run.find('id="run-flatten"')]
    flatten = run[run.find('id="run-flatten"') :]
    assert 'id="start-form"' in promote
    assert 'id="run-error"' in promote
    assert 'id="run-sleeves"' in book
    assert 'id="account-resume"' in recover
    assert 'id="account-kill"' not in recover
    assert 'id="account-kill"' in flatten
    assert 'id="account-kill-phrase"' in flatten
    assert 'id="account-kill-confirm"' in flatten
    assert 'id="account-resume"' not in flatten
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_css_run_kill_switch_zones(css_text: str) -> None:
    assert ".flatten-zone" in css_text
    assert ".recover-zone" in css_text
    assert ".flatten-zone .panel" in css_text
    assert ".flatten-zone .glance-heading" in css_text
```

e2e `test_control_plane_serves_help` GET `/`: also `assert 'id="run-flatten"' in html`.

`REQUIRED_PHRASES` add `"Flatten account"`.

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement HTML/CSS**

`index.html` `#screen-run`:

```html
    <section id="screen-run" class="screen" aria-label="Run">
      <div id="run-promote" class="glance-band">
        <h2 class="glance-heading">Start paper</h2>
        <div class="panel">
          <form id="start-form" class="inline">
            <!-- existing fields unchanged -->
          </form>
          <div id="run-error" class="error-box hidden"></div>
        </div>
      </div>
      <div id="run-book" class="glance-band">
        <h2 class="glance-heading">Sleeves</h2>
        <div id="run-sleeves"></div>
      </div>
      <div id="run-recover" class="glance-band recover-zone">
        <h2 class="glance-heading">After halt</h2>
        <div class="panel">
          <button type="button" id="account-resume" class="action warn">Resume after halt</button>
        </div>
      </div>
      <div id="run-flatten" class="glance-band flatten-zone">
        <h2 class="glance-heading">Flatten account</h2>
        <div class="panel">
          <label class="confirm-row">
            <input type="checkbox" id="account-kill-confirm">
            I understand this flattens the whole paper account
          </label>
          <label>
            Type FLATTEN
            <input type="text" id="account-kill-phrase" autocomplete="off" placeholder="FLATTEN">
          </label>
          <button type="button" id="account-kill" class="action danger account-kill">Kill account — flatten all</button>
        </div>
      </div>
    </section>
```

Keep the existing start-form labels/inputs/button exactly (same ids).

`styles.css` after `.glance-band` rules:

```css
.recover-zone .glance-heading {
  color: #f59e0b;
}

.flatten-zone {
  margin-top: 1.25rem;
}

.flatten-zone .glance-heading {
  color: #ef4444;
}

.flatten-zone .panel {
  border-color: #ef4444;
}
```

- [ ] **Step 4: HTML/CSS tests PASS.**

---

### Task 2: Help / README

`how_run` body:

```python
            "Run is four bands: Start paper, Sleeves, After halt, Flatten account. "
            "Start paper is a second explicit action. "
            "Stop zeros that sleeve on the next legal rebalance and does not flatten now. "
            "Sleeve kill flattens that sleeve, or the whole account if isolation is unclean. "
            "Resume lives under After halt and does not catch up. "
            "Account kill lives under Flatten account and requires typing FLATTEN."
```

README Operator account-kill bullet: add that Resume is under **After halt**, not beside flatten.

Full suite: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| four bands + isolated resume | 1 |
| louder flatten CSS | 1 |
| ids unchanged | 1 (no JS rewrite) |
| help/README | 2 |
