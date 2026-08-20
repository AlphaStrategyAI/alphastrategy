# Run Band-Local Errors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each Run band paints its own error; a refused account flatten is not shown under Start paper.

**Architecture:** Four `.error-box` mounts. `setRunError(band, message)` writes one and clears the others. No API change.

**Tech Stack:** HTML + `app.js` + helptext + pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-run-band-errors-requirements.md`](../requirements/2026-08-20-alphastrategy-run-band-errors-requirements.md)

## Global Constraints

- Paper only. Five screens. No `window.confirm`. Control ids for start/kill/resume stay.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `app.js`, `helptext.py`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_helptext.py`

---

### Task 1: Tests then markup + helper

- [ ] **Step 1: Failing tests**

```python
def test_html_run_band_errors(html_text: str) -> None:
    run = html_text[html_text.find('id="screen-run"') : html_text.find('id="screen-activity"')]
    promote = run[run.find('id="run-promote"') : run.find('id="run-book"')]
    book = run[run.find('id="run-book"') : run.find('id="run-recover"')]
    recover = run[run.find('id="run-recover"') : run.find('id="run-flatten"')]
    flatten = run[run.find('id="run-flatten"') :]
    assert 'id="run-error"' in promote
    assert 'id="run-sleeve-error"' in book
    assert 'id="run-recover-error"' in recover
    assert 'id="run-flatten-error"' in flatten
    assert 'id="run-flatten-error"' not in promote
    assert 'id="run-error"' not in flatten
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_set_run_error_by_band(js_text: str) -> None:
    assert "function setRunError" in js_text
    kill = js_text[js_text.find('getElementById("account-kill")') : js_text.find('getElementById("account-resume")')]
    assert 'setRunError("flatten"' in kill
    resume = js_text[js_text.find('getElementById("account-resume")') : js_text.find("function activeScreen")]
    assert 'setRunError("recover"' in resume
    assert 'setRunError("sleeves"' in js_text
    assert 'setRunError("promote"' in js_text
    assert "window.confirm" not in js_text
```

`REQUIRED_PHRASES` add `"own error"`.

- [ ] **Step 2: FAIL**

- [ ] **Step 3: Implement**

HTML: add error boxes in sleeves / recover / flatten panels (reuse `.error-box hidden`). Keep `#run-error` in Start paper.

`app.js` after `setError`:

```javascript
  function setRunError(band, message) {
    const ids = {
      promote: "run-error",
      sleeves: "run-sleeve-error",
      recover: "run-recover-error",
      flatten: "run-flatten-error",
    };
    for (const [key, id] of Object.entries(ids)) {
      const el = document.getElementById(id);
      if (!el) continue;
      setError(el, key === band ? message : "");
    }
  }
```

Replace `setError(document.getElementById("run-error"), ...)` in:
- `onStartSubmit` → `setRunError("promote", ...)`
- sleeve alloc / stop / kill → `setRunError("sleeves", ...)`
- account-kill → `setRunError("flatten", ...)`
- account-resume → `setRunError("recover", ...)`

`how_run` append: `Each Run band shows its own error.`

- [ ] **Step 4: Full suite green. Commit.**
