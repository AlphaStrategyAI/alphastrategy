# Risk Glance Bands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the Risk screen into Caps, Headroom, Tighten, and Sleeve overlays, and group tighten inputs as Gross / Names / Orders / Deltas.

**Architecture:** HTML bands + sticky wrapper kept on caps/headroom + `js/paint-risk.js` fieldset groups. Keep every form id and PUT key. Do not revive `static/app.js`. Tighten math and `riskFormIsDirty` stay.

**Tech Stack:** Static HTML/CSS, cockpit JS parts, `helptext.py`, pytest string tests, e2e GET `/`.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-risk-bands-requirements.md`](../requirements/2026-08-20-alphastrategy-risk-bands-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- Spoken labels stay `policyLabel(key)`. PUT bodies still use machine keys.
- Cockpit JS is assembled from `web/static/js/` parts. Edit `js/paint-risk.js`, not a file named `app.js`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `styles.css`, `js/paint-risk.js`
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_web_tokens.py`
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_e2e_mocked.py`

- [ ] **Step 1: Write the failing tests**

`tests/alphastrategy/test_web_tokens.py` (append):

```python
def test_html_risk_glance_bands(html_text: str) -> None:
    assert 'id="risk-caps"' in html_text
    assert 'id="risk-headroom"' in html_text
    assert 'id="risk-tighten"' in html_text
    assert 'id="risk-overlays"' in html_text
    assert '<h2 class="glance-heading">Caps</h2>' in html_text
    assert '<h2 class="glance-heading">Headroom</h2>' in html_text
    assert '<h2 class="glance-heading">Tighten</h2>' in html_text
    assert '<h2 class="glance-heading">Sleeve overlays</h2>' in html_text
    risk = html_text[html_text.find('id="screen-risk"') :]
    caps = risk[risk.find('id="risk-caps"') : risk.find('id="risk-headroom"')]
    head = risk[risk.find('id="risk-headroom"') : risk.find('id="risk-tighten"')]
    tighten = risk[risk.find('id="risk-tighten"') : risk.find('id="risk-overlays"')]
    overlays = risk[risk.find('id="risk-overlays"') :]
    assert 'id="risk-account-caps"' in caps
    assert 'id="risk-utilization"' in head
    assert 'id="risk-account-form"' in tighten
    assert 'id="risk-error"' in tighten
    assert 'id="risk-sleeves"' in overlays
    assert 'id="risk-account-form"' not in overlays
    sticky = html_text[
        html_text.find("risk-account-bar") : html_text.find('id="risk-tighten"')
    ]
    assert 'id="risk-caps"' in sticky
    assert 'id="risk-headroom"' in sticky
    assert 'id="risk-account-form"' not in sticky
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_css_risk_tighten_groups(css_text: str) -> None:
    assert ".risk-tighten-groups" in css_text
    assert ".risk-group" in css_text


def test_js_risk_tighten_groups(js_text: str) -> None:
    paint = js_text[
        js_text.find("RISK_TIGHTEN_GROUPS") : js_text.find("function renderRiskCaps")
    ]
    assert 'legend: "Gross"' in paint
    assert 'legend: "Names"' in paint
    assert 'legend: "Orders"' in paint
    assert 'legend: "Deltas"' in paint
    assert '"max_gross"' in paint
    assert '"max_names"' in paint
    assert '"max_orders_per_day"' in paint
    assert '"min_delta_dollar"' in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
    assert "createElement(\"fieldset\")" in js_text[
        js_text.find("function buildRiskInputs") : js_text.find("function validateTighten")
    ]
```

`REQUIRED_PHRASES` add `"Caps / Headroom / Tighten"`.

`test_control_plane_serves_help` GET `/`: `assert 'id="risk-tighten"' in html`.

- [ ] **Step 2: Run — FAIL**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_risk_glance_bands tests/alphastrategy/test_web_tokens.py::test_css_risk_tighten_groups tests/alphastrategy/test_web_tokens.py::test_js_risk_tighten_groups tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_e2e_mocked.py::test_control_plane_serves_help -q
```

Expected: FAIL (`risk-tighten` missing, phrase missing).

- [ ] **Step 3: Commit tests**

```bash
git add tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_helptext.py tests/alphastrategy/test_e2e_mocked.py
git commit -m "test: require Risk glance bands and grouped tighten"
```

---

### Task 2: Markup, CSS, painter, help

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`
- Modify: `src/alphastrategy/web/static/styles.css`
- Modify: `src/alphastrategy/web/static/js/paint-risk.js`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

- [ ] **Step 4: HTML**

Replace `#screen-risk` in `src/alphastrategy/web/static/index.html` with:

```html
    <section id="screen-risk" class="screen" aria-label="Risk">
      <div class="risk-account-bar">
        <div id="risk-caps" class="glance-band">
          <h2 class="glance-heading">Caps</h2>
          <div id="risk-account-caps" class="risk-caps nums"></div>
        </div>
        <div id="risk-headroom" class="glance-band">
          <h2 class="glance-heading">Headroom</h2>
          <div id="risk-utilization" class="risk-caps nums"></div>
        </div>
      </div>
      <div id="risk-tighten" class="glance-band">
        <h2 class="glance-heading">Tighten</h2>
        <div class="panel">
          <form id="risk-account-form"></form>
          <div id="risk-error" class="error-box hidden"></div>
        </div>
      </div>
      <div id="risk-overlays" class="glance-band">
        <h2 class="glance-heading">Sleeve overlays</h2>
        <div id="risk-sleeves"></div>
      </div>
    </section>
```

- [ ] **Step 5: CSS**

Delete `.risk-account-bar h2 { ... }` so `.glance-heading` wins.

Delete `#risk-utilization { margin-top: 0.65rem; }` (Headroom is its own band).

Add after `.risk-caps`:

```css
.risk-tighten-groups {
  display: grid;
  gap: 0.75rem;
}

@media (min-width: 800px) {
  .risk-tighten-groups {
    grid-template-columns: 1fr 1fr;
  }
}

.risk-group {
  border: 1px solid #2a3142;
  background: #0b0e14;
  border-radius: 4px;
  margin: 0;
  min-width: 0;
  padding: 0.5rem 0.65rem 0.65rem;
}

.risk-group legend {
  color: #9ba3b4;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  padding: 0 0.25rem;
  text-transform: uppercase;
}

.risk-group label {
  color: #9ba3b4;
  display: flex;
  flex-direction: column;
  font-size: 0.8rem;
  gap: 0.2rem;
  margin-top: 0.35rem;
}

#risk-account-form > .action {
  margin-top: 0.75rem;
}
```

- [ ] **Step 6: Painter**

At the top of `src/alphastrategy/web/static/js/paint-risk.js` (IIFE fragment, two-space indent):

```javascript
  const RISK_TIGHTEN_GROUPS = [
    { legend: "Gross", keys: ["max_gross", "max_name_weight", "max_order_notional_frac"] },
    { legend: "Names", keys: ["max_names"] },
    { legend: "Orders", keys: ["max_orders_per_rebalance", "max_orders_per_day"] },
    { legend: "Deltas", keys: ["min_delta_dollar", "min_delta_frac"] },
  ];
```

Replace `buildRiskInputs` with:

```javascript
  function buildRiskInputs(prefix, policy, current) {
    const form = document.createElement("form");
    form.dataset.prefix = prefix;
    const groups = document.createElement("div");
    groups.className = "risk-tighten-groups";
    for (const group of RISK_TIGHTEN_GROUPS) {
      const set = document.createElement("fieldset");
      set.className = "risk-group";
      const legend = document.createElement("legend");
      legend.textContent = group.legend;
      set.appendChild(legend);
      for (const key of group.keys) {
        const label = document.createElement("label");
        label.textContent = policyLabel(key);
        const input = document.createElement("input");
        input.type = "number";
        input.name = key;
        input.step =
          key.includes("frac") || key === "max_gross" || key === "max_name_weight"
            ? "0.01"
            : "1";
        input.placeholder = String(current[key]);
        input.dataset.current = String(current[key]);
        label.appendChild(input);
        set.appendChild(label);
      }
      groups.appendChild(set);
    }
    form.appendChild(groups);
    const submit = document.createElement("button");
    submit.type = "submit";
    submit.className = "action primary";
    submit.textContent = "Tighten";
    form.appendChild(submit);
    return form;
  }
```

Leave `renderRiskCaps`, `validateTighten`, `riskFormIsDirty`, and `renderRisk` unchanged except they keep using `buildRiskInputs`. File must stay ≤ 400 lines.

- [ ] **Step 7: Help + README**

`how_risk` body:

```python
            "Four bands: Caps / Headroom / Tighten, then Sleeve overlays. "
            "Account totals stay sticky. "
            "Tighten groups Gross / Names / Orders / Deltas. Tighten only; "
            "the form refuses looser values and still posts the policy keys."
```

Cockpit runbook, after the Risk names-caps sentence, add:

```text
Risk is four bands Caps / Headroom / Tighten plus Sleeve overlays.
```

README Quiet cockpit, after the spoken-label sentence, add:

```text
Risk is four bands: **Caps**, **Headroom**, **Tighten**, and **Sleeve overlays**.
Caps and Headroom stay sticky. Tighten groups **Gross / Names / Orders / Deltas**.
```

- [ ] **Step 8: Run tests — PASS**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

Expected: all pass. No real broker.

- [ ] **Step 9: Commit**

```bash
git add src/alphastrategy/web/static/index.html src/alphastrategy/web/static/styles.css src/alphastrategy/web/static/js/paint-risk.js src/alphastrategy/helptext.py README.md
git commit -m "feat: split Risk into caps, headroom, tighten, and overlays"
```

---

## Spec coverage

| Spec section | Task |
| --- | --- |
| Four regions + sticky | 2 HTML |
| Tighten groups | 2 JS + CSS |
| Keep ids / PUT keys | 2 HTML + painter |
| Help / README | 2 copy |
| Verification / e2e | 1 tests |

## Placeholder scan

None. Exact ids, group keys, CSS, painter, help strings, and commands.
