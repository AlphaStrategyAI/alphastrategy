# Screen-Aware Operator Help Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** F1 shows a short how-to for the current Quiet cockpit screen; the six-section runbook sits under Full runbook.

**Architecture:** `SCREEN_HOWTOS` lives in `helptext.py` next to `SECTIONS`. `help_payload()` adds `howtos`. CLI prints how-tos first. The aside paints `#help-howto` from `data-screen` and keeps essays in `#help-body` inside `<details id="help-runbook">`.

**Tech Stack:** Python helptext, stdlib HTTP, Quiet cockpit HTML/JS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-screen-help-requirements.md`](../requirements/2026-08-20-alphastrategy-screen-help-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Help is an aside, not a sixth tab. Locked tokens. No `window.confirm`. No live.
- Do not delete or reorder the six existing section ids.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/helptext.py`
- Modify: `src/alphastrategy/web/static/index.html`, `app.js`
- Modify: `README.md`
- Test: `tests/alphastrategy/test_helptext.py`, `test_web_tokens.py`, `test_api.py`, `test_e2e_mocked.py`

---

### Task 1: How-tos in helptext + API

**Files:**
- Modify: `src/alphastrategy/helptext.py`
- Test: `tests/alphastrategy/test_helptext.py`, `test_api.py`, `test_e2e_mocked.py`

- [ ] **Step 1: Failing tests**

`test_helptext.py`:

```python
HOWTO_SCREENS = ("portfolio", "strategies", "run", "activity", "risk")
HOWTO_IDS = (
    "how_portfolio",
    "how_strategies",
    "how_run",
    "how_activity",
    "how_risk",
)


def test_screen_howtos_match_five_screens() -> None:
    from alphastrategy.helptext import SCREEN_HOWTOS, help_payload, help_text

    assert tuple(item["screen"] for item in SCREEN_HOWTOS) == HOWTO_SCREENS
    assert tuple(item["id"] for item in SCREEN_HOWTOS) == HOWTO_IDS
    payload = help_payload()
    assert payload["howtos"] == SCREEN_HOWTOS
    ids = [section["id"] for section in payload["sections"]]
    assert ids == list(REQUIRED_IDS)
    text = help_text()
    assert "On Portfolio" in text
    assert "On Run" in text
    assert "Full runbook" not in text  # CLI has no details widget
    lower = text.lower()
    assert "halt is not flatten" in lower
```

Add `"On Portfolio"` to `REQUIRED_PHRASES`.

`test_api.py` in `test_get_help_returns_operator_sections`:

```python
    assert [item["id"] for item in payload["howtos"]] == [
        "how_portfolio",
        "how_strategies",
        "how_run",
        "how_activity",
        "how_risk",
    ]
```

e2e `test_control_plane_serves_help`: after help JSON, `assert help_body["howtos"][0]["id"] == "how_portfolio"`.

- [ ] **Step 2: Run — FAIL** (`SCREEN_HOWTOS` missing).

- [ ] **Step 3: Implement**

In `helptext.py` after `SECTIONS`:

```python
SCREEN_HOWTOS: list[dict[str, str]] = [
    {
        "id": "how_portfolio",
        "screen": "portfolio",
        "title": "On Portfolio",
        "body": (
            "Three bands: Book / Flatten budgets / Clock. Equity is the hero. "
            "The Positions Book column is wanted versus got. "
            "Header LIVE is the Supervisor beat, not Session OPEN."
        ),
    },
    {
        "id": "how_strategies",
        "screen": "strategies",
        "title": "On Strategies",
        "body": (
            "Upload a qualified .asb. Import is not permission to trade. "
            "Failures name the gate (hash, schema, conformance) and a next action. "
            "Start paper on Run."
        ),
    },
    {
        "id": "how_run",
        "screen": "run",
        "title": "On Run",
        "body": (
            "Start paper is a second explicit action. "
            "Stop zeros that sleeve on the next legal rebalance and does not flatten now. "
            "Sleeve kill flattens that sleeve, or the whole account if isolation is unclean. "
            "Account kill requires typing FLATTEN. Resume after halt does not catch up."
        ),
    },
    {
        "id": "how_activity",
        "screen": "activity",
        "title": "On Activity",
        "body": (
            "Time-ordered audit. Empty copy names the two legal rebalances. "
            "Kill rows say isolated residual or flattened account. "
            "Expand a row for the payload."
        ),
    },
    {
        "id": "how_risk",
        "screen": "risk",
        "title": "On Risk",
        "body": (
            "Account caps stay visible. Caps use desk words "
            "(Gross cap, Names, Orders today). Tighten only; "
            "the form refuses looser values and still posts the policy keys."
        ),
    },
]


def help_payload() -> dict[str, Any]:
    return {
        "title": HELP_TITLE,
        "sections": [dict(section) for section in SECTIONS],
        "howtos": [dict(item) for item in SCREEN_HOWTOS],
    }


def help_text() -> str:
    lines = [HELP_TITLE, ""]
    for item in SCREEN_HOWTOS:
        lines.append(item["title"])
        lines.append(item["body"])
        lines.append("")
    for section in SECTIONS:
        lines.append(section["title"])
        lines.append(section["body"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: Task 1 tests PASS.**

- [ ] **Step 5: Commit** `feat: add per-screen operator how-tos to helptext`

---

### Task 2: Aside markup + painters

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`, `app.js`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`

- [ ] **Step 1: Failing tests**

```python
def test_html_screen_help_howto(html_text: str) -> None:
    assert 'id="help-howto"' in html_text
    assert 'id="help-runbook"' in html_text
    assert "Full runbook" in html_text
    assert 'id="help-body"' in html_text
    assert 'data-screen="help"' not in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_renders_howto_for_active_screen(js_text: str) -> None:
    assert 'getElementById("help-howto")' in js_text
    assert "payload.howtos" in js_text
    assert "renderHelp(" in js_text
    assert "window.confirm" not in js_text
```

The `showScreen` function must call `renderHelp` when a payload is loaded. Assert:

```python
    show = js_text[js_text.find("function showScreen") : js_text.find("function setError")]
    assert "renderHelp" in show
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement**

`index.html` aside:

```html
    <aside id="help-panel" class="hidden" aria-label="Operator help">
      <h2>Operator help</h2>
      <div id="help-howto"></div>
      <details id="help-runbook">
        <summary>Full runbook</summary>
        <div id="help-body"></div>
      </details>
    </aside>
```

`showScreen`:

```javascript
  function showScreen(name) {
    document.querySelectorAll(".screen").forEach((el) => {
      el.classList.toggle("active", el.id === `screen-${name}`);
    });
    document.querySelectorAll("#nav button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.screen === name);
    });
    if (helpState.payload) {
      renderHelp(helpState.payload);
    }
  }
```

`helpState` must exist before `showScreen` — move `const helpState = { loaded: false, payload: null };` above `showScreen`, or keep it later and use a function-scoped object declared with `var` / hoist a `let helpState` at top of IIFE after `state`.

Put next to `state`:

```javascript
  const helpState = { loaded: false, payload: null };
```

Remove the later duplicate `const helpState`.

`renderHelp`:

```javascript
  function activeScreen() {
    const btn = document.querySelector("#nav button.active");
    return (btn && btn.dataset.screen) || "portfolio";
  }

  function renderHelp(payload) {
    helpState.payload = payload || helpState.payload;
    const howtoRoot = document.getElementById("help-howto");
    const body = document.getElementById("help-body");
    if (!howtoRoot || !body || !helpState.payload) return;
    const screen = activeScreen();
    const howtos = helpState.payload.howtos || [];
    const howto = howtos.find((item) => item.screen === screen) || howtos[0] || {};
    howtoRoot.innerHTML = "";
    const h = document.createElement("h3");
    h.textContent = howto.title || "";
    const p = document.createElement("p");
    p.textContent = howto.body || "";
    howtoRoot.appendChild(h);
    howtoRoot.appendChild(p);
    body.innerHTML = "";
    const title = document.createElement("p");
    title.className = "muted";
    title.textContent = helpState.payload.title || "Operator help";
    body.appendChild(title);
    for (const section of helpState.payload.sections || []) {
      const sh = document.createElement("h3");
      sh.textContent = section.title || "";
      const sp = document.createElement("p");
      sp.textContent = section.body || "";
      body.appendChild(sh);
      body.appendChild(sp);
    }
  }
```

`loadHelp` sets `helpState.payload` via `renderHelp(payload)` and `helpState.loaded = true`.

README Quiet cockpit: F1 is how-to for the current screen; **Full runbook** is the same six sections as `alphastrategy help`.

Optional CSS: `details#help-runbook { margin-top: 0.75rem; }` using existing tokens only. Summary color `#9ba3b4`.

- [ ] **Step 4: Full suite green.**

- [ ] **Step 5: Commit** `feat: show F1 how-to for the active Quiet cockpit screen`

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| SCREEN_HOWTOS + payload + CLI | 1 |
| Aside howto + details runbook | 2 |
| Re-paint on showScreen | 2 |
| Five screens / no confirm | 2 |
| README | 2 |
