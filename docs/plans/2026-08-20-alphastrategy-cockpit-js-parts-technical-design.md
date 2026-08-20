# Quiet Cockpit JS Parts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Assemble `/app.js` from seven screen-shaped files so the cockpit is maintainable without a bundler or a behavior change.

**Architecture:** `alphastrategy.web.cockpit.cockpit_js()` concatenates `JS_PARTS` and wraps one IIFE. The HTTP server returns that string for `/app.js`. Tests use the same function.

**Tech Stack:** Python 3 stdlib HTTP, static JS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-cockpit-js-parts-requirements.md`](../requirements/2026-08-20-alphastrategy-cockpit-js-parts-requirements.md)

## Global Constraints

- Paper only. Five screens. No `window.confirm`. No npm. One `<script src="app.js">`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Create: `src/alphastrategy/web/__init__.py`, `src/alphastrategy/web/cockpit.py`
- Create: `src/alphastrategy/web/static/js/{core,paint-portfolio,paint-strategies,paint-run,paint-activity,paint-risk,boot}.js`
- Delete: `src/alphastrategy/web/static/app.js`
- Modify: `src/alphastrategy/api/app.py`, `helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_api.py`, `test_helptext.py`

---

### Task 1: Failing bundle contract

- [ ] **Step 1: Tests**

`tests/alphastrategy/test_web_tokens.py` — add, and keep `js_text` reading `app.js` until Task 2 (or switch in Task 2).

```python
def test_cockpit_js_assembled_from_parts() -> None:
    from alphastrategy.web.cockpit import JS_PARTS, STATIC_DIR, cockpit_js

    assert JS_PARTS == (
        "js/core.js",
        "js/paint-portfolio.js",
        "js/paint-strategies.js",
        "js/paint-run.js",
        "js/paint-activity.js",
        "js/paint-risk.js",
        "js/boot.js",
    )
    for rel in JS_PARTS:
        path = STATIC_DIR / rel
        assert path.is_file(), rel
        nlines = path.read_text(encoding="utf-8").count("\n")
        assert nlines <= 400, f"{rel} has {nlines} newlines"
    assert not (STATIC_DIR / "app.js").is_file()
    blob = cockpit_js()
    assert blob.startswith("(function () {")
    assert blob.rstrip().endswith("})();")
    assert "function setRunError" in blob
    assert "function renderPortfolio" in blob
    assert "window.confirm" not in blob
```

`REQUIRED_PHRASES` add `"js/core.js"` or `"assembled from js/"`. Use `"assembled from js/"`.

`test_api.py` `test_get_static_assets`: after GET `/app.js`,

```python
    from alphastrategy.web.cockpit import cockpit_js
    assert js.body == cockpit_js().encode("utf-8")
```

- [ ] **Step 2: FAIL** (module / parts missing).

---

### Task 2: Implement assemble + split

- [ ] **Step 3:** `src/alphastrategy/web/cockpit.py`:

```python
"""Assemble Quiet cockpit JavaScript from screen-shaped parts."""
from __future__ import annotations

from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent / "static"

JS_PARTS: tuple[str, ...] = (
    "js/core.js",
    "js/paint-portfolio.js",
    "js/paint-strategies.js",
    "js/paint-run.js",
    "js/paint-activity.js",
    "js/paint-risk.js",
    "js/boot.js",
)

_HEAD = '(function () {\n  "use strict";\n\n'
_TAIL = "})();\n"


def cockpit_js() -> str:
    chunks: list[str] = []
    for rel in JS_PARTS:
        text = (STATIC_DIR / rel).read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        chunks.append(text)
    return _HEAD + "".join(chunks) + _TAIL
```

Empty `web/__init__.py`.

Split current `app.js` **inner body** (after `"use strict";` blank line, before closing `})();`) into the seven files at these 1-based inclusive ranges of today's `app.js`:

| File | Lines |
| --- | --- |
| core.js | 4–211 |
| paint-portfolio.js | 212–573 |
| paint-strategies.js | 574–615 |
| paint-run.js | 616–707 |
| paint-activity.js | 708–794 |
| paint-risk.js | 795–906 |
| boot.js | 907–1226 |

Do not include the IIFE wrap in the parts.

`api/app.py` `_serve_static`: if `path` in `("/app.js", "/static/app.js")`, write `cockpit_js().encode("utf-8")` with javascript content-type. Other routes unchanged.

Delete `static/app.js`.

Change `js_text` fixture to `return cockpit_js()`. Change `test_static_files_exist` to assert HTML, CSS, and each `JS_PARTS` file; not `app.js`.

Update `test_js_sleeve_kill_does_not_require_flatten_phrase` so it does not require `onImportSubmit` to follow `killSleeve`:

```python
    start = js_text.index("async function killSleeve")
    nxt = js_text.find("\n  async function ", start + 1)
    kill_fn = js_text[start : nxt if nxt != -1 else None]
    assert "FLATTEN" not in kill_fn
```

Help cockpit or walls: `Quiet cockpit JS is assembled from js/ parts. The browser still loads /app.js.`

README tree: `web/static/js/`  # cockpit parts; GET /app.js assembles them

- [ ] **Step 4:** Full suite green.

- [ ] **Step 5: Commit**
