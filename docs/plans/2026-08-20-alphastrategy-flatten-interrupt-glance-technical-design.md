# Flatten Interrupt Glance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the host died mid-flatten, the flatten banner and Activity flatten row say interrupted flattening instead of looking like a typed FLATTEN.

**Architecture:** `_flatten_account(reason=...)` writes flatten audit reason. Recover records `last_kill.reason=flatten_interrupted`. `renderBanners` forks flatten copy on that reason. Kill-outcome banner stays hidden for it.

**Tech Stack:** Python supervisor, Quiet cockpit JS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-flatten-interrupt-glance-requirements.md`](../requirements/2026-08-20-alphastrategy-flatten-interrupt-glance-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- JS must not contain `Gross cap`. Do not label a tile Live.
- `renderBanners` keeps a single `const reason` (halt). Reuse `killReason` for the flatten fork.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never hit a real broker.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/js/paint-activity.js`, `src/alphastrategy/helptext.py`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Tests**

In `test_restart_during_flattening_finishes_flatten`, after the flatten-event assert:

```python
    assert restarted.snapshot.last_kill["reason"] == "flatten_interrupted"
    flattens = [event for event in events if event["event"] == "flatten"]
    assert flattens[-1]["reason"] == "flatten_interrupted"
```

In `test_web_tokens.py` add:

```python
def test_js_flatten_banner_names_interrupted_flattening(js_text: str) -> None:
    block = js_text.split("function renderBanners")[1].split("function renderPortfolio")[0]
    assert "FLAT: paper account flattened" in block
    assert "flatten_interrupted" in block
    assert "FLAT: interrupted flattening — paper account flattened" in block
    assert block.count("const reason") == 1
    assert "window.confirm" not in js_text


def test_js_activity_flatten_interrupted(js_text: str) -> None:
    flatten_branch = js_text.split('case "flatten":')[1].split("default:")[0]
    assert "flatten_interrupted" in flatten_branch
    assert "interrupted flattening" in flatten_branch
```

`REQUIRED_PHRASES` add `"flatten banner names interrupted flattening"`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_restart_during_flattening_finishes_flatten tests/alphastrategy/test_web_tokens.py::test_js_flatten_banner_names_interrupted_flattening tests/alphastrategy/test_web_tokens.py::test_js_activity_flatten_interrupted tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

Expected: last_kill missing / JS copy missing / help phrase missing.

---

### Task 2: Supervisor, banners, help

- [ ] **Step 3: loop.py**

Change `_flatten_account` to `def _flatten_account(self, *, reason: str = "account") -> None:` and audit `self._audit("flatten", scope="account", reason=reason)`.

`_recover_interrupted_flatten`:

```python
        self._flatten_account(reason="flatten_interrupted")
        self._record_kill(
            KillOutcome(
                isolated=False,
                flattened=True,
                scope="account",
                reason="flatten_interrupted",
                bundle_id=None,
            )
        )
```

- [ ] **Step 4: paint-portfolio.js** — Move `lastKill` / `killReason` to just after the halt `const reason`. Flatten block:

```javascript
    if (flattened) {
      flattenEl.classList.remove("hidden");
      flattenEl.textContent =
        killReason === "flatten_interrupted"
          ? "FLAT: interrupted flattening — paper account flattened"
          : "FLAT: paper account flattened";
    } else {
      flattenEl.classList.add("hidden");
    }
```

Do not declare a second `const reason`. Kill-outcome `else` still hides `flatten_interrupted`.

- [ ] **Step 5: paint-activity.js** — `case "flatten":`

```javascript
        if (ev.reason === "flatten_interrupted") {
          return "interrupted flattening";
        }
        return ev.scope || "account";
```

- [ ] **Step 6: helptext.py** — In `halt_flatten`, after the interrupted-flattening sentence, add: `The flatten banner names interrupted flattening when the host died mid-close_all.`

- [ ] **Step 7: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass. `test_js_render_banners_declares_reason_once` still passes. Isolate-crash last_kill remains `fallback_interrupted`.

---

## Spec coverage

Recover last_kill, flatten audit reason, banner fork, Activity, help — tasked. No new banner id. No placeholders.
