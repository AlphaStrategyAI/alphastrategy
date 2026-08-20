# Limit-Breach Flatten Glance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Name a cap-triggered flatten on `last_kill`, the flatten banner, and the Activity flatten row so it is not silent next to a typed FLATTEN.

**Architecture:** `FlattenRequested` grows `reason="limit"`. `tick` flattens with that reason and `_record_kill`. Cockpit reuses `killReason` in `renderBanners` (keep a single halt `const reason`). Activity `eventSummary` flatten branch maps `limit` → `limit breach`.

**Tech Stack:** Supervisor, Quiet cockpit JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-limit-flatten-glance-requirements.md`](../requirements/2026-08-20-alphastrategy-limit-flatten-glance-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live. No WebSockets. No charts.
- `renderBanners` keeps a **single** `const reason` (halt). Reuse `killReason` for flatten forks.
- `"Gross cap"` must not appear in assembled JS.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/errors.py`, `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/js/paint-activity.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_risk.py` (optional reason assert)

`check_book` / `plan_orders` keep `FlattenRequested("account")`; default `reason="limit"` covers them.

---

### Task 1: Failing tests

- [ ] **Step 1: Supervisor**

In `test_limit_breach_flattens_account`, after the existing asserts:

```python
    assert supervisor.snapshot.last_kill is not None
    assert supervisor.snapshot.last_kill["reason"] == "limit"
    assert supervisor.snapshot.last_kill["flattened"] is True
    assert supervisor.snapshot.last_kill["scope"] == "account"
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    flattens = [ev for ev in events if ev.get("event") == "flatten"]
    assert flattens[-1]["reason"] == "limit"
```

Confirm the actual audit filename via `_make_supervisor` / `home.audit_path()` in that file. Use the same helper other tests use (`json.loads` on audit path).

- [ ] **Step 2: JS + help**

Add:

```python
def test_js_flatten_banner_names_limit_breach(js_text: str) -> None:
    block = js_text.split("function renderBanners")[1].split("function renderPortfolio")[0]
    assert "FLAT: limit breach — paper account flattened" in block
    assert 'killReason === "limit"' in block or "killReason === 'limit'" in block
    assert block.count("const reason") == 1
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text


def test_js_activity_flatten_limit_breach(js_text: str) -> None:
    flatten_branch = js_text.split('case "flatten":')[1].split("default:")[0]
    assert 'ev.reason === "limit"' in flatten_branch or "ev.reason === 'limit'" in flatten_branch
    assert "limit breach" in flatten_branch
```

`REQUIRED_PHRASES` add `"flatten banner names a limit breach"`.

- [ ] **Step 3: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_limit_breach_flattens_account tests/alphastrategy/test_web_tokens.py::test_js_flatten_banner_names_limit_breach tests/alphastrategy/test_web_tokens.py::test_js_activity_flatten_limit_breach tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

Expected: FAIL (`last_kill` missing / copy missing).

---

### Task 2: Implementation

- [ ] **Step 4: Exception** — `FlattenRequested.__init__(self, scope: str, reason: str = "limit")` stores `self.reason`.

- [ ] **Step 5: tick** — `except FlattenRequested as exc:` flatten with `exc.reason`, then `_record_kill` with that reason.

- [ ] **Step 6: JS** — flatten banner third fork for `limit`. Activity flatten `limit` → `limit breach`. No second `const reason`.

- [ ] **Step 7: Help + README** — flatten banner names a limit breach; Activity flatten rows say limit breach.

- [ ] **Step 8: Full suite PASS. Commit.**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: PASS.

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| last_kill + audit `limit` | 1, 4, 5 |
| Flatten banner copy | 2, 6 |
| Activity copy | 2, 6 |
| Help | 2, 7 |
| Single `const reason` | 2, 6 |
