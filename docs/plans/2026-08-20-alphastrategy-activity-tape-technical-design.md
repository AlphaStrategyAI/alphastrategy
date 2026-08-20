# Activity Tape Bands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split Activity into Beat, Tape, and Blotter so exception counts are first glance and the JSON expand list is the detail tape.

**Architecture:** HTML bands + `js/paint-activity.js` counts from existing `state.activity`. Keep `#activity-heartbeat` and `#activity-list`. No API/audit schema change. Do not revive `static/app.js`.

**Tech Stack:** Static HTML/CSS, cockpit JS parts, `helptext.py`, pytest string tests, e2e GET `/`.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-activity-tape-requirements.md`](../requirements/2026-08-20-alphastrategy-activity-tape-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- Kill-row copy (isolated residual / flattened account) stays.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `js/paint-activity.js`
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`
- CSS: reuse `.metrics-4` / `.metric.hero` / status colors. No new tokens required.

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`tests/alphastrategy/test_web_tokens.py` (append):

```python
def test_html_activity_tape_bands(html_text: str) -> None:
    assert 'id="act-beat"' in html_text
    assert 'id="act-tape"' in html_text
    assert 'id="act-blotter"' in html_text
    assert '<h2 class="glance-heading">Beat</h2>' in html_text
    assert '<h2 class="glance-heading">Tape</h2>' in html_text
    assert '<h2 class="glance-heading">Blotter</h2>' in html_text
    act = html_text[
        html_text.find('id="screen-activity"') : html_text.find('id="screen-risk"')
    ]
    beat = act[act.find('id="act-beat"') : act.find('id="act-tape"')]
    tape = act[act.find('id="act-tape"') : act.find('id="act-blotter"')]
    blotter = act[act.find('id="act-blotter"') :]
    assert 'id="activity-heartbeat"' in beat
    assert 'id="act-count-rebalance"' in tape
    assert 'id="act-count-halt"' in tape
    assert 'id="act-count-deviation"' in tape
    assert 'id="act-count-kill"' in tape
    assert "hero" in tape
    assert 'id="activity-list"' in blotter
    assert 'id="activity-list"' not in tape
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_paints_activity_tape(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderActivity") : js_text.find("RISK_TIGHTEN_GROUPS")
    ]
    assert '"act-count-rebalance"' in paint
    assert '"act-count-halt"' in paint
    assert '"act-count-deviation"' in paint
    assert '"act-count-kill"' in paint
    assert '"status-running"' in paint
    assert '"status-halt"' in paint
    assert '"status-fail"' in paint
    assert 'event === "rebalance"' in paint
    assert 'event === "execution_deviation"' in paint
    assert 'event === "flatten"' in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

`REQUIRED_PHRASES` add `"Beat / Tape / Blotter"`.

e2e GET `/`: `assert 'id="act-tape"' in html`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

---

### Task 2: Markup, painter, help

- [ ] **Step 4: HTML**

Replace `#screen-activity` with:

```html
    <section id="screen-activity" class="screen" aria-label="Activity">
      <div id="act-beat" class="glance-band">
        <h2 class="glance-heading">Beat</h2>
        <p id="activity-heartbeat" class="muted"></p>
      </div>
      <div id="act-tape" class="glance-band">
        <h2 class="glance-heading">Tape</h2>
        <div class="metrics metrics-4 nums">
          <div class="metric hero">
            <div class="metric-label">Rebalances</div>
            <div id="act-count-rebalance" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Halts</div>
            <div id="act-count-halt" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Deviations</div>
            <div id="act-count-deviation" class="metric-value">—</div>
          </div>
          <div class="metric">
            <div class="metric-label">Kills</div>
            <div id="act-count-kill" class="metric-value">—</div>
          </div>
        </div>
      </div>
      <div id="act-blotter" class="glance-band">
        <h2 class="glance-heading">Blotter</h2>
        <ul id="activity-list" class="activity-list nums"></ul>
      </div>
    </section>
```

- [ ] **Step 5: Painter**

In `renderActivity`, after `const events = state.activity || [];` and after painting the beat line, count and paint tiles **before** the empty-list return:

```javascript
    const counts = { rebalance: 0, halt: 0, deviation: 0, kill: 0 };
    for (const ev of events) {
      if (ev.event === "rebalance") counts.rebalance += 1;
      else if (ev.event === "halt") counts.halt += 1;
      else if (ev.event === "execution_deviation") counts.deviation += 1;
      else if (ev.event === "kill" || ev.event === "flatten") counts.kill += 1;
    }
    const setTape = (elId, value, onClass) => {
      const el = document.getElementById(elId);
      if (!el) return;
      el.textContent = String(value);
      if (onClass) el.classList.toggle(onClass, value > 0);
    };
    setTape("act-count-rebalance", counts.rebalance, "status-running");
    setTape("act-count-halt", counts.halt, "status-halt");
    setTape("act-count-deviation", counts.deviation, "status-fail");
    setTape("act-count-kill", counts.kill, "status-fail");
```

Keep empty-copy and expand-row behavior after that.

- [ ] **Step 6: Help + README**

`how_activity` body:

```python
            "Three bands: Beat / Tape / Blotter. Rebalances is the hero count. "
            "Halt, deviation, and kill tiles are not quiet when above zero. "
            "Time-ordered audit. Empty copy names the two legal rebalances. "
            "Kill rows say isolated residual or flattened account. "
            "Expand a blotter row for the payload."
```

Cockpit: `Activity is three bands Beat / Tape / Blotter.`

README Quiet cockpit: same three names.

- [ ] **Step 8: Full suite PASS. Commit.**

---

## Spec coverage

Bands, tape counts, colors, keep blotter ids, help, e2e — all tasked. No placeholders.
