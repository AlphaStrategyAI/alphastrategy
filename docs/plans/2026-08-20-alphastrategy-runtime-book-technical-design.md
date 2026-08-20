# Runtime Overlay Digest and Book Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `runtime.yaml` overlay bytes drive spoken policy even on same-size rewrite; Book Equity names Beat or Glance.

**Architecture:** `_read_runtime` and the spoken cache key use SHA-256 of runtime yaml bytes. `live_book_source()` reports sticky vs glance. GET status/portfolio expose `book.source`. Equity subcopy paints Beat/Glance from rails.

**Tech Stack:** Supervisor, HTTP handlers, Quiet cockpit JS, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-runtime-book-requirements.md`](../requirements/2026-08-20-alphastrategy-runtime-book-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. GET status/risk must not flatten.
- Do not use `live_book()` inside `_equity()` / `_enforce_live_book`.
- Each file in `JS_PARTS` stays ≤ 400 newlines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_web_tokens.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Runtime overlays load once until the file changes",
    "Book Equity names Beat or Glance",
```

Replace `test_spoken_policy_sees_runtime_yaml_write` body so the second write freezes mtime and size:

```python
def test_spoken_policy_sees_runtime_yaml_write(tmp_path: Path) -> None:
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    home = AlphaStrategyHome(root=tmp_path)
    (home.bundle_dir("asb_test") / "risk-envelope.yaml").write_text(
        "max_name_weight: 0.20\n", encoding="utf-8"
    )
    runtime = home.runtime_path()
    runtime.write_text(
        "sleeve_overlays:\n  asb_test:\n    max_name_weight: 0.10\n",
        encoding="utf-8",
    )
    supervisor.start_sleeve("asb_test", 0.25)
    assert supervisor.spoken_policy().max_name_weight == pytest.approx(0.10)
    prior = runtime.stat()
    runtime.write_text(
        "sleeve_overlays:\n  asb_test:\n    max_name_weight: 0.05\n",
        encoding="utf-8",
    )
    os.utime(runtime, ns=(prior.st_atime_ns, prior.st_mtime_ns))
    assert runtime.stat().st_size == prior.st_size
    assert runtime.stat().st_mtime_ns == prior.st_mtime_ns
    assert supervisor.spoken_policy().max_name_weight == pytest.approx(0.05)
```

After `test_sleeve_policies_read_runtime_once`:

```python
def test_read_runtime_parses_once_while_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loads = {"n": 0}
    orig = yaml.safe_load

    def counted(data):
        loads["n"] += 1
        return orig(data)

    monkeypatch.setattr("alphastrategy.supervisor.loop.yaml.safe_load", counted)
    home = AlphaStrategyHome(root=tmp_path)
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    home.runtime_path().write_text(
        yaml.safe_dump({"sleeve_overlays": {"asb_test": {"max_name_weight": 0.10}}}),
        encoding="utf-8",
    )
    supervisor.start_sleeve("asb_test", 0.25)
    supervisor.spoken_policy()
    after = loads["n"]
    supervisor.spoken_policy()
    supervisor.sleeve_policies(["asb_test"])
    assert loads["n"] == after
    assert after >= 1
```

In `tests/alphastrategy/test_api.py` after `test_heartbeat_live_book_holds_past_ttl_for_status_and_portfolio`:

```python
def test_status_book_source_glance_without_tick(api_stack) -> None:
    client, _home, _supervisor, _broker = api_stack
    body = client.get("/api/status").json()
    assert body["book"]["source"] == "glance"


def test_status_book_source_heartbeat_after_tick(api_stack) -> None:
    client, _home, supervisor, _broker = api_stack
    supervisor.tick()
    body = client.get("/api/status").json()
    assert body["book"]["source"] == "heartbeat"


def test_status_book_source_glance_after_kill(api_stack) -> None:
    client, _home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 15.0}
    supervisor.tick()
    killed = client.post("/api/paper/kill", json={})
    assert killed.status == 200
    body = client.get("/api/status").json()
    assert body["book"]["source"] == "glance"
```

In `tests/alphastrategy/test_web_tokens.py` inside `test_html_glance_bands`, after `id="metric-equity"`:

```python
    assert 'id="metric-equity-sub"' in book
```

New test near other paint locks:

```python
def test_js_paints_book_equity_beat_or_glance(js_text: str) -> None:
    rails = js_text[js_text.find("function bookSourceLabel") :]
    assert "function bookSourceLabel" in js_text
    assert '"heartbeat"' in rails or "=== \"heartbeat\"" in rails or "=== 'heartbeat'" in rails
    assert "Beat " in rails
    assert "Glance" in rails
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_halt_flatten.py::test_spoken_policy_sees_runtime_yaml_write \
  tests/alphastrategy/test_halt_flatten.py::test_read_runtime_parses_once_while_unchanged \
  tests/alphastrategy/test_api.py::test_status_book_source_glance_without_tick \
  tests/alphastrategy/test_api.py::test_status_book_source_heartbeat_after_tick \
  tests/alphastrategy/test_api.py::test_status_book_source_glance_after_kill \
  tests/alphastrategy/test_web_tokens.py::test_html_glance_bands \
  tests/alphastrategy/test_web_tokens.py::test_js_paints_book_equity_beat_or_glance \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL on frozen runtime rewrite, missing `book.source`, missing Equity sub / `bookSourceLabel`, missing help phrases.

If `test_read_runtime_parses_once_while_unchanged` PASSES on RED (stamp cache already skips yaml), keep it as a lock.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git commit -m "test: runtime overlay digest; Book Equity Beat or Glance"
```

---

### Task 2: Engine + API + paint + help

- [ ] **Step 1: Runtime digest**

`__init__`: `self._runtime_doc_cache: tuple[str, dict[str, Any]] | None = None`

```python
    def _read_runtime(self) -> dict[str, Any]:
        path = self._home.runtime_path()
        if not path.is_file():
            raw = b""
            digest = ""
        else:
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
        cached = self._runtime_doc_cache
        if cached is not None and cached[0] == digest:
            return cached[1]
        if not raw:
            doc: dict[str, Any] = {}
        else:
            loaded = yaml.safe_load(raw.decode("utf-8"))
            doc = loaded if isinstance(loaded, dict) else {}
        self._runtime_doc_cache = (digest, doc)
        return doc
```

`_spoken_cache_key` first tuple item: `self._file_digest(self._home.runtime_path())`.

```python
    def live_book_source(self) -> str:
        with self._lock:
            cached = self._live_book_cache
            if cached is None:
                return "none"
            return "heartbeat" if cached[3] else "glance"
```

- [ ] **Step 2: Handlers**

`handle_get_status`: after building the dict, utilization already ran; add `"book": {"source": supervisor.live_book_source()}`.

`handle_get_portfolio`: after `live_book()`, add `"book": {"source": supervisor.live_book_source()}`.

- [ ] **Step 3: HTML + JS**

In `index.html` Equity metric, after `#metric-equity`:

```html
            <div id="metric-equity-sub" class="metric-sub">—</div>
```

In `paint-rails.js` after `finiteNumber`:

```javascript
  function bookSourceLabel() {
    const src = state.status && state.status.book && state.status.book.source;
    const age =
      state.status && state.status.heartbeat && state.status.heartbeat.age_seconds;
    if (src === "heartbeat") {
      return Number.isFinite(age) ? "Beat " + age + "s" : "Beat";
    }
    if (src === "glance") return "Glance";
    return "—";
  }
```

In `renderPortfolio` after setting `#metric-equity`:

```javascript
    const eqSub = document.getElementById("metric-equity-sub");
    if (eqSub) eqSub.textContent = bookSourceLabel();
```

- [ ] **Step 4: Help / README**

Execution after envelope sentence: `Runtime overlays load once until the file changes.`

`how_risk` after sleeve envelopes: same.

`how_portfolio` after heartbeat holds: `Book Equity names Beat or Glance.`

README heartbeat bullet: both new sentences.

- [ ] **Step 5: Targeted tests then full suite**

Keep `test_spoken_policy_sees_envelope_yaml_write`.
Keep `test_heartbeat_live_book_holds_past_ttl`.
Keep `test_html_has_no_live_toggle_label`.
Keep `test_js_part_files_stay_small`.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: digest runtime overlays; Book Equity names Beat or Glance"
```
