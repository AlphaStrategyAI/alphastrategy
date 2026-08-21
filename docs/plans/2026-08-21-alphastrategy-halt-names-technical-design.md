# HALT names Start paper that cannot seed last weights holds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When Start paper cannot seed last sleeve weights, the HALT banner, After halt, and `status` stderr name that health halt in desk words instead of the engine string.

**Architecture:** Keep persisted `halt_reason`. Map the seed prefix at the paint/CLI edge: `formatHaltBanner` in `js/core.js`, After halt in `paint-run.js`, `_status_halt_line` in the CLI. Do not flatten. Do not rewrite snapshot halt_reason. Keep exact Start hint copy.

**Tech Stack:** Python 3.9+, pytest, cockpit JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-halt-names-requirements.md`](../requirements/2026-08-21-alphastrategy-halt-names-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET.
- Keep exact `Start paper while halted waits for resume. Resume does not catch up.`
- Keep exact Start hint seed-hold sentence.
- Keep `renderBanners` a single `const reason`.
- `paint-portfolio.js` and `paint-rails.js` stay ≤ 400 lines. Put the mapper in `js/core.js`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/core.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/js/paint-run.js`, `src/alphastrategy/cli/main.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_web_tokens.py`
- Modify: `tests/alphastrategy/test_cli.py`

**Interfaces:**
- Consumes: status `halted` / `halt_reason`; assembled cockpit JS
- Produces: HALT desk words for seed prefix; help phrases `HALT names Start paper that cannot seed last weights holds` and `status names HALT`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add after `Start paper that cannot seed last weights holds`:

```python
    "HALT names Start paper that cannot seed last weights holds",
    "status names HALT",
```

In `test_web_tokens.py` after `test_js_paints_run_halt_reason`:

```python
def test_js_paints_halt_banner_seed_hold(js_text: str) -> None:
    banners = js_text[
        js_text.find("function renderBanners") : js_text.find("function renderPortfolio")
    ]
    assert "formatHaltBanner" in banners
    assert banners.count("const reason") == 1
    mapper = js_text[
        js_text.find("function formatHaltBanner") : js_text.find("function formatContributionCell")
    ]
    assert "start paper that cannot seed last weights holds" in mapper
    assert "start paper seeds last sleeve weights" in mapper
    assert "Gross cap" not in js_text
    assert "Order size" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

In `test_js_paints_run_halt_reason` after `Resume is only after halt.`:

```python
    assert "Start paper that cannot seed last weights holds. Resume does not catch up." in paint
    assert "start paper seeds last sleeve weights" in paint
```

Keep `innerHTML not in paint`. Keep `test_js_paints_run_start_hint` exact waits-for-resume.

In `test_cli.py` after `test_status_prints_unknown_limit_on_stderr`:

```python
def test_status_prints_seed_halt_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "halted",
        "clock": {},
        "halted": True,
        "halt_reason": "start paper seeds last sleeve weights: no evaluator for sleeve asb_z",
        "flattened": False,
        "utilization": {},
        "book": {"source": "glance"},
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "BOOK: glance",
        "HALT: start paper that cannot seed last weights holds",
    ]
    patch_alpaca.assert_not_called()


def test_status_prints_halt_reason_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "halted",
        "clock": {},
        "halted": True,
        "halt_reason": "stale bars",
        "flattened": False,
        "utilization": {},
        "book": {"source": "glance"},
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "BOOK: glance",
        "HALT: stale bars",
    ]
    patch_alpaca.assert_not_called()
```

Keep `test_status_prints_book_on_stderr` exact `["BOOK: heartbeat"]`.
Keep `test_status_prints_pnl_on_stderr` exact BOOK / PNL / LIMIT lines.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_paints_halt_banner_seed_hold tests/alphastrategy/test_web_tokens.py::test_js_paints_run_halt_reason tests/alphastrategy/test_web_tokens.py::test_js_paints_run_start_hint tests/alphastrategy/test_cli.py::test_status_prints_seed_halt_on_stderr tests/alphastrategy/test_cli.py::test_status_prints_halt_reason_on_stderr tests/alphastrategy/test_cli.py::test_status_prints_book_on_stderr tests/alphastrategy/test_cli.py::test_status_prints_pnl_on_stderr tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: mapper / After halt / status HALT / help fail. BOOK / PNL / Start hint locks still pass.

- [ ] **Step 3: Commit tests and docs**

```bash
git add docs/requirements/2026-08-21-alphastrategy-halt-names-requirements.md docs/plans/2026-08-21-alphastrategy-halt-names-technical-design.md tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_cli.py tests/alphastrategy/test_helptext.py
git commit -m "test: HALT names Start paper that cannot seed last weights holds"
```

---

### Task 2: Implement

**Files:**
- Modify: `src/alphastrategy/web/static/js/core.js`
- Modify: `src/alphastrategy/web/static/js/paint-portfolio.js`
- Modify: `src/alphastrategy/web/static/js/paint-run.js`
- Modify: `src/alphastrategy/cli/main.py`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

- [ ] **Step 4: Mapper + banner + After halt + status**

In `js/core.js` immediately before `formatContributionCell`:

```javascript
  function formatHaltBanner(reason, fallback) {
    const text = String(reason || "");
    if (/start paper seeds last sleeve weights/i.test(text)) {
      return "start paper that cannot seed last weights holds";
    }
    return text || fallback || "halted";
  }
```

In `renderBanners` replace the halt text assignment with:

```javascript
      haltEl.textContent = "HALT: " + formatHaltBanner(reason, state.status && state.status.state);
```

Keep `const reason` once. File stays ≤ 400 lines.

In `renderRunRecover` halted/reason branch:

```javascript
      el.textContent = /start paper seeds last sleeve weights/i.test(String(reason))
        ? "Start paper that cannot seed last weights holds. Resume does not catch up."
        : reason || (state.status && state.status.state) || "halted";
```

Keep idle `Resume is only after halt.` No `innerHTML`. File ≤ 400 lines.

`cli/main.py` next to `_LIMIT_UNKNOWN_STATUS`:

```python
_HALT_SEED_STATUS = "HALT: start paper that cannot seed last weights holds"


def _status_halt_line(payload: dict[str, Any]) -> str | None:
    if not payload.get("halted"):
        return None
    text = str(payload.get("halt_reason") or "").lower()
    if "start paper seeds last sleeve weights" in text:
        return _HALT_SEED_STATUS
    reason = payload.get("halt_reason") or payload.get("state") or "halted"
    return f"HALT: {reason}"
```

`_print_status`: after PNL, before LIMIT, print `_status_halt_line` when not None.

- [ ] **Step 5: Help and README**

Add `HALT names Start paper that cannot seed last weights holds. ` to `execution` (after Start paper that cannot seed last weights holds), `halt_flatten` (same), `how_portfolio` (after The deviation banner follows Book Drift…), `how_run` (after After halt shows the halt reason).

Add `status names HALT. ` to `cli` after status names Day PnL.

README Operator after Start paper that cannot seed last weights holds. Keep `Next rebalance`.

- [ ] **Step 6: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 7: Commit, push, update PR**

```bash
git add src/alphastrategy/web/static/js/core.js src/alphastrategy/web/static/js/paint-portfolio.js src/alphastrategy/web/static/js/paint-run.js src/alphastrategy/cli/main.py src/alphastrategy/helptext.py README.md
git commit -m "feat: HALT names Start paper that cannot seed last weights holds"
```
