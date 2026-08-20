# Interrupt Glance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show interrupted rebalancing on After halt, and show interrupted sleeve isolate on the kill-outcome banner and Activity kill row.

**Architecture:** Extend existing `#kill-outcome-banner` and Activity `eventSummary`. Add `#run-halt-reason` mount in `#run-recover`. Add `reason` on the recover isolate `kill` audit. No new API object.

**Tech Stack:** Quiet cockpit HTML/JS, helptext, pytest string tests. Supervisor audit field only.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-interrupt-glance-requirements.md`](../requirements/2026-08-20-alphastrategy-interrupt-glance-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- JS must not contain `Gross cap`. Do not label a tile Live.
- Do not `innerHTML = ""` on `#run-recover`. Keep `#run-recover-error`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never hit a real broker.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/js/paint-run.js`, `src/alphastrategy/web/static/js/paint-activity.js`, `src/alphastrategy/web/static/js/boot.js`, `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/helptext.py`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_halt_flatten.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Tests**

In `tests/alphastrategy/test_web_tokens.py` `test_js_renders_kill_outcome_from_last_kill`, add:

```python
    assert "fallback_interrupted" in js_text
    assert "interrupted sleeve isolate — whole paper account flattened" in js_text
```

In `test_js_activity_kill_summary_distinguishes_isolated`, add:

```python
    assert "fallback_interrupted" in kill_branch
    assert "interrupted sleeve isolate" in kill_branch
```

In `test_html_run_kill_switch_zones`, after `assert 'id="account-resume"' in recover`, add:

```python
    assert 'id="run-halt-reason"' in recover
    assert 'id="run-halt-reason"' not in flatten
```

Add:

```python
def test_js_paints_run_halt_reason(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRunRecover") : js_text.find("function eventSummary")
    ]
    assert "run-halt-reason" in paint
    assert "halt_reason" in paint
    assert "Resume is only after halt." in paint
    assert "innerHTML" not in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

`REQUIRED_PHRASES` add `"After halt shows the halt reason"`.

In `test_restart_during_sleeve_isolate_flattens_account`, after last_kill asserts, add:

```python
    kills = [event for event in json.loads_lines if false]
```

Use the same events parse pattern as other tests in that file:

```python
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    kills = [event for event in events if event["event"] == "kill"]
    assert kills
    assert kills[-1]["reason"] == "fallback_interrupted"
```

- [ ] **Step 2: Run — FAIL.** Commit tests.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_renders_kill_outcome_from_last_kill tests/alphastrategy/test_web_tokens.py::test_js_activity_kill_summary_distinguishes_isolated tests/alphastrategy/test_web_tokens.py::test_html_run_kill_switch_zones tests/alphastrategy/test_web_tokens.py::test_js_paints_run_halt_reason tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_halt_flatten.py::test_restart_during_sleeve_isolate_flattens_account -q`

Expected: JS/HTML/help fail missing copy and `#run-halt-reason`. Isolate test fails missing `reason` on kill audit.

---

### Task 2: Paint, audit, help

- [ ] **Step 3: index.html** — Inside `#run-recover` `.panel`, **before** `#account-resume`:

```html
          <p id="run-halt-reason" class="muted">Resume is only after halt.</p>
```

- [ ] **Step 4: paint-portfolio.js** — In `renderBanners`, extend the sleeve-kill `else if` for fallback flatten to include `fallback_interrupted` as its own branch **before** the generic fallback_error branch:

```javascript
    } else if (killReason === "fallback_interrupted") {
      killEl.className = "banner fail";
      killEl.textContent =
        "SLEEVE KILL: interrupted sleeve isolate — whole paper account flattened";
    } else if (killReason === "fallback_not_ready" || killReason === "fallback_error") {
```

- [ ] **Step 5: paint-run.js** — After `renderRunSleeves`, add:

```javascript
  function renderRunRecover() {
    const el = document.getElementById("run-halt-reason");
    if (!el) return;
    const halted = state.status && state.status.halted;
    const reason =
      (state.portfolio && state.portfolio.halt_reason) ||
      (state.status && state.status.halt_reason) ||
      "";
    if (halted || reason) {
      el.className = "warn";
      el.textContent = reason || (state.status && state.status.state) || "halted";
      return;
    }
    el.className = "muted";
    el.textContent = "Resume is only after halt.";
  }
```

`boot.js` `refresh`: after the `if (!runFormIsDirty()) { renderRunSleeves(); }` block, call `renderRunRecover();` unconditionally.

- [ ] **Step 6: paint-activity.js** — In `case "kill":`, before the isolated true/false branches:

```javascript
        if (ev.reason === "fallback_interrupted") {
          return `interrupted sleeve isolate ${id}`.trim();
        }
```

- [ ] **Step 7: loop.py** — Recover isolate audit:

```python
        self._audit(
            "kill",
            bundle_id=bundle_id,
            isolated=False,
            reason="fallback_interrupted",
        )
```

- [ ] **Step 8: helptext.py** — In `how_run`, after “Resume lives under After halt and does not catch up.”, add: `After halt shows the halt reason.`

- [ ] **Step 9: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass. `test_js_paints_run_capacity` still finds `renderRunSleeves`. `test_js_render_banners_declares_reason_once` still has one `const reason` in `renderBanners` (do not add another `const reason` there).

---

## Spec coverage

Kill-outcome row, After halt mount, Activity copy, recover audit reason, help — tasked. No placeholders. Crash-recovery actions unchanged except the audit field.
