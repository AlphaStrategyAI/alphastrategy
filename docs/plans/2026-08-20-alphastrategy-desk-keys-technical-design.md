# Desk Keyboard Accelerators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Alt+1–5 switches Quiet cockpit screens; F1 toggles Help; a muted header hint makes the chords discoverable.

**Architecture:** Static HTML + one keydown handler next to the existing Escape listener. No Supervisor change.

**Tech Stack:** Quiet cockpit JS, pytest string tests.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-desk-keys-requirements.md`](../requirements/2026-08-20-alphastrategy-desk-keys-requirements.md)

## Global Constraints

- Five `#nav` screens. No `window.confirm`. Paper only. Locked tokens.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `styles.css`, `app.js`
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_helptext.py`

---

### Task 1: HTML hint + aria-keyshortcuts + CSS

**Files:** `index.html`, `styles.css`, `test_web_tokens.py`

- [ ] **Step 1: Failing test**

```python
def test_html_keyboard_accelerators(html_text: str) -> None:
    assert 'id="kbd-hint"' in html_text
    assert "Alt+1–5" in html_text or "Alt+1-5" in html_text
    assert "F1 help" in html_text
    assert 'aria-keyshortcuts="Alt+1"' in html_text
    assert 'aria-keyshortcuts="Alt+5"' in html_text
    assert 'aria-keyshortcuts="F1"' in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]
```

- [ ] **Step 2:** Run `pytest tests/alphastrategy/test_web_tokens.py::test_html_keyboard_accelerators -q` — FAIL missing `#kbd-hint`.

- [ ] **Step 3: HTML/CSS**

Header after `.brand`:

```html
    <span id="kbd-hint" class="kbd-hint">Alt+1–5 · F1 help</span>
```

Nav buttons: `aria-keyshortcuts="Alt+1"` … `Alt+5` in order. Help toggle: `aria-keyshortcuts="F1"`.

CSS:

```css
.kbd-hint {
  font-size: 0.72rem;
  color: #5c6573;
  letter-spacing: 0.02em;
}
```

- [ ] **Step 4:** Run the test — PASS.

- [ ] **Step 5:** Commit `feat: expose Alt+1-5 and F1 on the Quiet cockpit header`

---

### Task 2: keydown handler

**Files:** `app.js`, `test_web_tokens.py`

- [ ] **Step 1: Failing test**

```python
def test_js_alt_digit_and_f1_accelerators(js_text: str) -> None:
    assert "Digit1" in js_text
    assert "Digit5" in js_text
    assert 'ev.key === "F1"' in js_text or 'ev.key==="F1"' in js_text
    assert "altKey" in js_text
    assert "preventDefault" in js_text
    assert 'ev.key === "1"' not in js_text
```

- [ ] **Step 2:** Run it — FAIL.

- [ ] **Step 3: JS** after the Escape listener, replace/extend the keydown handler:

```javascript
  const SCREEN_KEYS = {
    Digit1: "portfolio",
    Digit2: "strategies",
    Digit3: "run",
    Digit4: "activity",
    Digit5: "risk",
  };

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") {
      setHelpOpen(false);
      return;
    }
    if (ev.ctrlKey || ev.metaKey) return;
    if (ev.key === "F1") {
      ev.preventDefault();
      const open =
        document.getElementById("help-toggle").getAttribute("aria-expanded") === "true";
      setHelpOpen(!open);
      return;
    }
    if (!ev.altKey) return;
    const screen = SCREEN_KEYS[ev.code];
    if (!screen) return;
    ev.preventDefault();
    showScreen(screen);
  });
```

Remove the old Escape-only listener so there is one keydown handler.

- [ ] **Step 4:** `pytest tests/alphastrategy/test_web_tokens.py -q` — PASS.

- [ ] **Step 5:** Commit `feat: Alt+1-5 switches screens; F1 toggles Help`

---

### Task 3: Help + README + suite

Add `"Alt+1"` to `REQUIRED_PHRASES` (exact substring in `text`). Cockpit help: `Alt+1 through Alt+5 switch screens. F1 toggles Help.` README Quiet cockpit one line.

- [ ] Full suite `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

---

## Self-review

Alt+1–5, F1, hint, aria, no bare digit, five screens, help copy — all tasked. No TBD.
