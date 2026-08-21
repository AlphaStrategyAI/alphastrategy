# Resume does not seed last weights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After Resume, missing last sleeve weights stay named on Run, Activity, HALT, and status instead of looking all-clear.

**Architecture:** Do not seed on `resume()`. Paint `live_limit.kind === "unknown"` on Start hint and After halt. Map `no evaluator for sleeve` in `formatHaltBanner` and CLI HALT after the Start paper prefix check. Activity halt summaries use that mapper.

**Tech Stack:** Python 3.9+, pytest, cockpit JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-resume-seed-requirements.md`](../requirements/2026-08-21-alphastrategy-resume-seed-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET.
- Do not call `_seed_last_sleeve_weights` from `resume()`.
- Keep exact `Start paper while halted waits for resume. Resume does not catch up.`
- Keep exact Start hint seed-hold sentence.
- Keep `renderBanners` a single `const reason`.
- `paint-portfolio.js` and `paint-rails.js` stay ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/core.js`, `src/alphastrategy/web/static/js/paint-run.js`, `src/alphastrategy/web/static/js/paint-activity.js`, `src/alphastrategy/cli/main.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_api.py`
- Modify: `tests/alphastrategy/test_web_tokens.py`
- Modify: `tests/alphastrategy/test_cli.py`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` after `After halt is four tiles Reason / Spent / Next / Resume`:

```python
    "Resume does not seed last weights",
    "Activity halt rows name Start paper that cannot seed last weights holds",
```

In `test_api.py` after `test_start_paper_seed_failure_returns_held_with_halt_reason`:

```python
def test_resume_after_seed_failure_keeps_unknown_limit(api_stack):
    client, home, supervisor, broker = api_stack
    home.bundle_dir("asb_z").mkdir(parents=True, exist_ok=True)
    close_all_before = broker.close_all_count
    started = client.post("/api/paper/start", json={"bundle_id": "asb_z", "allocation": 0.18})
    assert started.status == 200
    assert started.json()["held"] is True
    resumed = client.post("/api/paper/resume", json={})
    assert resumed.status == 200
    body = client.get("/api/status").json()
    assert body["halted"] is False
    assert body["utilization"]["live_limit"]["kind"] == "unknown"
    assert supervisor.snapshot.sleeves["asb_z"] == pytest.approx(0.18)
    assert not (supervisor.snapshot.last_sleeve_weights.get("asb_z") or {})
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "halted"
```

In `test_js_paints_run_start_hint` after the seed-hold sentence assert:

```python
    assert "Resume does not seed last weights. Start paper seeds last sleeve weights." in paint
    assert 'kind === "unknown"' in paint
```

Keep exact waits-for-resume. Keep `innerHTML` not in paint.

In `test_js_paints_run_halt_reason` after `"wait"`:

```python
    assert "Resume does not seed last weights. Start paper seeds last sleeve weights." in paint
    assert 'kind === "unknown"' in paint
    assert '"weights"' in paint
```

In `test_js_paints_halt_banner_seed_hold` mapper asserts, add:

```python
    assert "resume does not seed last weights" in mapper
    assert "no evaluator for sleeve" in mapper
```

New `test_js_activity_halt_names_seed_hold` after `test_js_activity_kill_summary_distinguishes_isolated`:

```python
def test_js_activity_halt_names_seed_hold(js_text: str) -> None:
    halt_branch = js_text.split('case "halt":')[1].split('case "rebalance":')[0]
    assert "formatHaltBanner" in halt_branch
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

In `test_cli.py` after `test_status_prints_halt_reason_on_stderr`:

```python
def test_status_prints_resume_seed_halt_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "halted",
        "clock": {},
        "halted": True,
        "halt_reason": "no evaluator for sleeve asb_z",
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
        "HALT: resume does not seed last weights",
    ]
    patch_alpaca.assert_not_called()
```

Keep `test_status_prints_seed_halt_on_stderr` and `test_status_prints_book_on_stderr`.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_resume_after_seed_failure_keeps_unknown_limit tests/alphastrategy/test_api.py::test_start_paper_seed_failure_returns_held_with_halt_reason tests/alphastrategy/test_web_tokens.py::test_js_paints_run_start_hint tests/alphastrategy/test_web_tokens.py::test_js_paints_run_halt_reason tests/alphastrategy/test_web_tokens.py::test_js_paints_halt_banner_seed_hold tests/alphastrategy/test_web_tokens.py::test_js_activity_halt_names_seed_hold tests/alphastrategy/test_cli.py::test_status_prints_resume_seed_halt_on_stderr tests/alphastrategy/test_cli.py::test_status_prints_seed_halt_on_stderr tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: resume unknown / hint / After halt / mapper / Activity / CLI resume-HALT / help fail. Seed-hold locks still pass.

- [ ] **Step 3: Commit tests and docs**

```bash
git add docs/requirements/2026-08-21-alphastrategy-resume-seed-requirements.md docs/plans/2026-08-21-alphastrategy-resume-seed-technical-design.md tests/alphastrategy/test_api.py tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_cli.py tests/alphastrategy/test_helptext.py
git commit -m "test: Resume does not seed last weights"
```

---

### Task 2: Implement

**Files:**
- Modify: `src/alphastrategy/web/static/js/core.js`
- Modify: `src/alphastrategy/web/static/js/paint-run.js`
- Modify: `src/alphastrategy/web/static/js/paint-activity.js`
- Modify: `src/alphastrategy/cli/main.py`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

- [ ] **Step 4: Mapper, Run, Activity, CLI**

`formatHaltBanner` after the seed-prefix branch:

```javascript
    if (/no evaluator for sleeve/i.test(text)) {
      return "resume does not seed last weights";
    }
```

`renderRunStartHint` after flatten, before idle:

```javascript
    if (utilization().live_limit && utilization().live_limit.kind === "unknown") {
      el.className = "warn";
      el.textContent =
        "Resume does not seed last weights. Start paper seeds last sleeve weights.";
      return;
    }
```

`renderRunRecover`: when not active and `utilization().live_limit.kind === "unknown"`, paint Reason/Next `weights` warn, Resume `—`, hint the same sentence as Start hint. Halted/reason still win. Keep spent rule. No `innerHTML`. File ≤ 400 lines.

Activity `case "halt":` return `formatHaltBanner(ev.reason, "halt")`. Keep drill-in `["Reason", ev.reason]`.

CLI `_HALT_RESUME_SEED_STATUS = "HALT: resume does not seed last weights"`. `_status_halt_line`: after seed prefix, if `"no evaluator for sleeve"` in text, return that line.

- [ ] **Step 5: Help and README**

Phrases into the sections listed in the requirements. README Operator after After halt is four tiles. Keep `Next rebalance`.

- [ ] **Step 6: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 7: Commit, push, update PR**

```bash
git add src/alphastrategy/web/static/js/core.js src/alphastrategy/web/static/js/paint-run.js src/alphastrategy/web/static/js/paint-activity.js src/alphastrategy/cli/main.py src/alphastrategy/helptext.py README.md
git commit -m "feat: Resume does not seed last weights"
```
