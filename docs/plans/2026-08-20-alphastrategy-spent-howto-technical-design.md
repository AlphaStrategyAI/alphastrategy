# Spent How-to Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the current spent-window desk in Help, and stop the empty Positions table from promising a rebalance that Last already spent.

**Architecture:** Add `task_spent` to `TASK_HOWTOS`. Update `tutorial_first_session` chrome. `renderPortfolio` empty copy forks on `last_rebalance_complete === false`.

**Tech Stack:** `helptext.py`, Quiet cockpit JS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-spent-howto-requirements.md`](../requirements/2026-08-20-alphastrategy-spent-howto-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Keep tutorial from requiring a live fill or flatten. Keep substring `Next rebalance`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/helptext.py`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `README.md`
- Test: `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_api.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Help ids + phrases + JS copy**

`test_task_howtos_match_jobs` tuple add `"task_spent"` after `"task_wanted"`.

`test_get_help` (in `test_api.py`) tasks list add `"task_spent"`.

`REQUIRED_PHRASES` add `"How to read a spent window"` and `"Clock Last is spent"`.

In `test_tutorials_come_before_how_to_jobs` add:

```python
    assert "Roster names imported at" in item["body"]
    assert "Session / Now / Next / Last" in item["body"]
    assert "Next rebalance" in item["body"]
```

In `test_js_first_glance_behaviors` add:

```python
    assert "Clock Last is spent. Resume does not catch up." in js_text
    assert "last_rebalance_complete" in js_text[
        js_text.find("function renderPortfolio") : js_text.find("function pulseLabel")
    ]
```

Keep existing `The next legal open or close rebalance will trade.`

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py::test_task_howtos_match_jobs tests/alphastrategy/test_helptext.py::test_tutorials_come_before_how_to_jobs tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases tests/alphastrategy/test_web_tokens.py::test_js_first_glance_behaviors tests/alphastrategy/test_api.py::test_get_help -q`

If `test_get_help` has a different name, use the test that asserts `payload["tasks"]` ids.

---

### Task 2: Implementation

- [ ] **Step 3: Tutorial + `task_spent`**

Tutorial body steps 2–4 become:

```text
2. Open Strategies (Alt+2). Under Import .asb upload the file.
You will see Inventory Imported count 1. Roster names imported at. You are not trading yet.
3. Open Run (Alt+3). Under Start paper pick the bundle, set a small allocation,
check Confirm paper start, then Start paper.
You will see the sleeve on Run. Clock is Session / Now / Next / Last. Next is the hero.
Portfolio Clock shows Next rebalance. Last stays an em dash until a session event is spent or finishes.
4. Open Portfolio Positions. Empty rows until the next legal rebalance are expected.
Book Drift stays an em dash or 0 until then.
You finished the lesson when the sleeve is on Run and Clock shows Next rebalance.
Do not use Flatten account in this lesson.
```

Keep the opener (import + start, will not flatten) and step 1.

Append to `TASK_HOWTOS`:

```python
    {
        "id": "task_spent",
        "screens": ["portfolio", "activity", "run"],
        "title": "How to read a spent window",
        "body": (
            "1. On Portfolio, Clock Last names the spent window. "
            "2. On Activity, Tape Rebalances sub names spent. "
            "3. The deviation banner follows Book Drift and cannot go quiet while Drift is above zero. "
            "4. On Run, After halt names the spent session event. "
            "Resume does not catch up. Clock Last is spent until a later event finishes."
        ),
    },
```

- [ ] **Step 4: empty Positions copy**

In `renderPortfolio` empty paper-sleeve branch:

```javascript
        empty =
          state.status && state.status.last_rebalance_complete === false
            ? "No positions yet. Clock Last is spent. Resume does not catch up."
            : "No positions yet. The next legal open or close rebalance will trade.";
```

- [ ] **Step 5: README**

Operator: Help includes How to read a spent window. Empty Positions names a spent Last.

- [ ] **Step 6: Full suite PASS.** Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

---
