# Named Working Blotter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Book, Activity Beat, and Risk Headroom headings name Beat or Glance; CLI `status` names BOOK on stderr.

**Architecture:** Reuse `bookSourceLabel()`. `paintBookSourceHeadings()` fills three heading spans. Offline status JSON gains `book`. `_print_status` emits `BOOK: heartbeat|glance` on stderr before LIMIT.

**Tech Stack:** Quiet cockpit HTML/CSS/JS, CLI, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-named-book-requirements.md`](../requirements/2026-08-20-alphastrategy-named-book-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. GET status/risk must not flatten.
- CLI stdout is one JSON object. BOOK and LIMIT go to stderr.
- Offline status keeps `from_supervisor(..., live=False)`.
- Each file in `JS_PARTS` stays ≤ 400 newlines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/cli/main.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Book, Beat, and Headroom name Beat or Glance",
    "status names BOOK heartbeat or glance",
```

In `test_html_glance_bands`, replace the exact Book heading lock and add the source id:

```python
    assert '<h2 class="glance-heading">Book' in html_text
    assert 'id="book-source"' in book
```

In `test_html_risk_glance_bands`:

```python
    assert '<h2 class="glance-heading">Headroom' in html_text
```

and inside `head`:

```python
    assert 'id="risk-book-source"' in head
```

In `test_html_activity_tape_bands`:

```python
    assert '<h2 class="glance-heading">Beat' in html_text
```

and inside `beat`:

```python
    assert 'id="act-book-source"' in beat
```

New JS lock next to `test_js_paints_book_equity_beat_or_glance`:

```python
def test_js_paints_book_source_headings(js_text: str) -> None:
    assert "function paintBookSourceHeadings" in js_text
    assert "book-source" in js_text
    assert "act-book-source" in js_text
    assert "risk-book-source" in js_text
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

In `test_status_prints_json` after heartbeat asserts:

```python
    assert payload["book"]["source"] == "none"
```

After `test_status_prints_limit_on_stderr`:

```python
def test_status_prints_book_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "idle_in_session",
        "clock": {},
        "halted": False,
        "flattened": False,
        "utilization": {},
        "heartbeat": {"age_seconds": 4, "pulse": "live", "interval_seconds": 20},
        "book": {"source": "heartbeat"},
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    out = json.loads(captured.out.strip())
    assert out["book"]["source"] == "heartbeat"
    assert captured.err.splitlines() == ["BOOK: heartbeat"]
    patch_alpaca.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_web_tokens.py::test_html_glance_bands \
  tests/alphastrategy/test_web_tokens.py::test_html_risk_glance_bands \
  tests/alphastrategy/test_web_tokens.py::test_html_activity_tape_bands \
  tests/alphastrategy/test_web_tokens.py::test_js_paints_book_source_headings \
  tests/alphastrategy/test_cli.py::test_status_prints_json \
  tests/alphastrategy/test_cli.py::test_status_prints_book_on_stderr \
  tests/alphastrategy/test_cli.py::test_status_prints_limit_on_stderr \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL on missing heading ids, missing `paintBookSourceHeadings`, missing offline `book`, missing BOOK stderr, missing help phrases.

`test_status_prints_limit_on_stderr` should still PASS (LIMIT unchanged).

- [ ] **Step 3: Commit failing tests + docs**

```bash
git commit -m "test: name Book Beat Headroom and status BOOK"
```

---

### Task 2: Paint + CLI + help

- [ ] **Step 1: HTML + CSS**

```html
        <h2 class="glance-heading">Book <span id="book-source" class="glance-source"></span></h2>
```

```html
        <h2 class="glance-heading">Beat <span id="act-book-source" class="glance-source"></span></h2>
```

```html
          <h2 class="glance-heading">Headroom <span id="risk-book-source" class="glance-source"></span></h2>
```

```css
.glance-source {
  color: #5c6573;
  font-weight: 500;
  letter-spacing: 0.04em;
}
```

- [ ] **Step 2: JS**

In `paint-rails.js` after `bookSourceLabel`:

```javascript
  function paintBookSourceHeadings() {
    const label = bookSourceLabel();
    const text = label === "—" ? "" : label;
    ["book-source", "act-book-source", "risk-book-source"].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    });
  }
```

At the end of `renderDeskPulse`, call `paintBookSourceHeadings();`.

- [ ] **Step 3: CLI**

```python
_BOOK_STATUS = "BOOK: {source}"
```

```python
def _status_book_line(payload: dict[str, Any]) -> str | None:
    book = payload.get("book") if isinstance(payload.get("book"), dict) else None
    if not isinstance(book, dict):
        return None
    source = book.get("source")
    if source not in ("heartbeat", "glance"):
        return None
    return _BOOK_STATUS.format(source=source)


def _print_status(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, separators=(",", ":")))
    book_line = _status_book_line(payload)
    if book_line:
        print(book_line, file=sys.stderr)
    line = _status_limit_line(payload)
    if line:
        print(line, file=sys.stderr)
```

Offline payload adds `"book": {"source": supervisor.live_book_source()}`.

- [ ] **Step 4: Help / README**

`how_portfolio` after Equity sentence: `Book, Beat, and Headroom name Beat or Glance.`

`how_activity` after Beat tiles: same.

`how_risk` after Headroom tiles: same.

CLI/status help: `status names BOOK heartbeat or glance.`

README after Equity sentence / LIMIT: both new sentences.

- [ ] **Step 5: Targeted tests then full suite**

Keep `test_html_has_no_live_toggle_label`.
Keep `test_js_paints_book_equity_beat_or_glance`.
Keep `test_status_omits_limit_when_flattened`.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: name Book Beat Headroom and status BOOK"
```
