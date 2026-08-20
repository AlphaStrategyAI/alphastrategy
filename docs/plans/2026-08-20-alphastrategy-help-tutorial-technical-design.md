# First Paper Session Tutorial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Diátaxis tutorial, Your first paper session, as the first Help layer in CLI, API, and the Quiet cockpit aside.

**Architecture:** Canonical `TUTORIALS` in `helptext.py`. Payload key `tutorials`. CLI prints tutorials before How to jobs. Aside `#help-tutorial` is always painted. Screen how-tos and jobs stay.

**Tech Stack:** `helptext.py`, cockpit HTML/CSS/JS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-help-tutorial-requirements.md`](../requirements/2026-08-20-alphastrategy-help-tutorial-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- Help stays an aside. Tutorial title does **not** start with `How to`.
- Keep `#help-howto`, `#help-tasks`, `#help-runbook`. Each JS part ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/helptext.py`, `index.html`, `styles.css`, `js/boot.js`, `README.md`, `docs/index.md`
- Test: `test_helptext.py`, `test_web_tokens.py`, `test_api.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: helptext**

`REQUIRED_PHRASES` add `"Your first paper session"`.

Append:

```python
def test_tutorials_come_before_how_to_jobs() -> None:
    from alphastrategy.helptext import TUTORIALS

    assert tuple(item["id"] for item in TUTORIALS) == ("tutorial_first_session",)
    payload = help_payload()
    assert payload["tutorials"] == TUTORIALS
    item = TUTORIALS[0]
    assert item["title"] == "Your first paper session"
    assert not item["title"].startswith("How to")
    assert "You will see" in item["body"]
    assert "You finished the lesson" in item["body"]
    assert "Flatten account" in item["body"]
    text = help_text()
    assert text.index("Your first paper session") < text.index(
        "How to import a qualified .asb"
    )
```

Update `test_help_copy_is_this_product` to include `TUTORIALS` bodies in the blob.

`test_task_howtos_match_jobs` keep How to import before On Portfolio.

- [ ] **Step 2: HTML/JS/API/e2e**

`test_html_help_tasks`: also `assert 'id="help-tutorial"' in html_text` and tutorial appears before howto:

```python
    assert html_text.find('id="help-tutorial"') < html_text.find('id="help-howto"')
```

Add:

```python
def test_js_renders_help_tutorial(js_text: str) -> None:
    paint = js_text[js_text.find("function renderHelp") : js_text.find("async function loadHelp")]
    assert "payload.tutorials" in paint
    assert 'getElementById("help-tutorial")' in paint
    assert "window.confirm" not in js_text
```

`test_css_help_panel_is_aside_not_modal` or new:

```python
def test_css_help_tutorial_uses_running_token(css_text: str) -> None:
    block = re.search(r"#help-tutorial h3\s*\{[^}]*\}", css_text)
    assert block is not None
    assert "#10b981" in block.group(0).lower()
```

`test_get_help_returns_operator_sections`:

```python
    assert [item["id"] for item in payload["tutorials"]] == ["tutorial_first_session"]
```

e2e `test_control_plane_serves_help`: `assert help_body["tutorials"][0]["id"] == "tutorial_first_session"` and `'id="help-tutorial"' in html`.

- [ ] **Step 3: Run — FAIL.** Commit tests.

---

### Task 2: Copy, HTML, JS, docs

- [ ] **Step 4: `TUTORIALS` in `helptext.py`** as requirements §2. `help_payload` / `help_text` order as §3.

Cockpit body, replace the F1 sentences with:

```text
F1 opens Help. Help starts with Your first paper session, then the screen how-to and the jobs for that screen.
```

- [ ] **Step 5: HTML** insert `#help-tutorial` as the first child after `<h2>Operator help</h2>`.

- [ ] **Step 6: CSS**

```css
#help-tutorial h3 {
  color: #10b981;
}
```

- [ ] **Step 7: `renderHelp`** paint `payload.tutorials` into `#help-tutorial` (title h3, body p) before howtos. Skip if the mount is missing.

- [ ] **Step 8: README + `docs/index.md`** as requirements §4.

- [ ] **Step 9: Full suite PASS. Commit.**

---

## Spec coverage

Tutorial copy, payload, CLI order, aside mount, green heading, docs — tasked. No placeholders.
