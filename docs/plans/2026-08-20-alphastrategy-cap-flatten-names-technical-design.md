# Cap Flatten Names Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store the policy key on a cap flatten and paint it with `policyLabel` so the flatten banner matches Caps tiles.

**Architecture:** `check_book` / `plan_orders` pass `reason=<key>` into `FlattenRequested`. `tick` already persists that reason. Cockpit maps cap keys through `policyLabel`; keeps `limit` for old snapshots. Do not put `Gross cap` in JS.

**Tech Stack:** Supervisor, Quiet cockpit JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-cap-flatten-names-requirements.md`](../requirements/2026-08-20-alphastrategy-cap-flatten-names-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/risk/check.py`, `src/alphastrategy/supervisor/orders.py`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/js/paint-activity.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_orders.py`, `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Python reasons**

In each `test_check_book_*_flattens*` add `assert exc.value.reason == "<key>"` (`long_only`, `max_gross`, `max_name_weight`, `max_names`).

In `test_plan_orders_raises_flatten_on_*` add `max_order_notional_frac`, `max_orders_per_rebalance`, `max_orders_per_day`.

In `test_limit_breach_flattens_account` change expected `last_kill` / audit reason from `"limit"` to `"max_gross"`.

- [ ] **Step 2: JS + help**

Extend `test_js_flatten_banner_names_limit_breach` (or add `test_js_flatten_banner_names_breached_cap`):

```python
def test_js_flatten_banner_names_breached_cap(js_text: str) -> None:
    block = js_text.split("function renderBanners")[1].split("function renderPortfolio")[0]
    assert "policyLabel(killReason)" in block
    assert "NUMERIC_CAPS" in block
    assert "long_only" in block
    assert "FLAT: limit breach — paper account flattened" in block
    assert block.count("const reason") == 1
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text


def test_js_activity_flatten_names_breached_cap(js_text: str) -> None:
    flatten_branch = js_text.split('case "flatten":')[1].split("default:")[0]
    assert "policyLabel(ev.reason)" in flatten_branch
    assert "NUMERIC_CAPS" in flatten_branch
    assert "limit breach" in flatten_branch
```

`REQUIRED_PHRASES` add `"flatten banner names the breached cap"`.

- [ ] **Step 3: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_risk.py::test_check_book_gross_breach_flattens_account tests/alphastrategy/test_halt_flatten.py::test_limit_breach_flattens_account tests/alphastrategy/test_web_tokens.py::test_js_flatten_banner_names_breached_cap tests/alphastrategy/test_web_tokens.py::test_js_activity_flatten_names_breached_cap tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

---

### Task 2: Implementation

- [ ] **Step 4:** `check_book` / `plan_orders` pass the reason keys from the requirements table.

- [ ] **Step 5:** Flatten banner: cap key → `"FLAT: " + policyLabel(killReason) + " — paper account flattened"`. Activity flatten: `policyLabel(ev.reason) + " breach"`. Keep `limit` / interrupted / generic forks. Cap test: `killReason === "long_only" || NUMERIC_CAPS.indexOf(killReason) !== -1`.

- [ ] **Step 6:** Help + README with `flatten banner names the breached cap`.

- [ ] **Step 7:** Full suite PASS. Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| Per-raise keys | 1, 4 |
| last_kill max_gross | 1, 4 |
| policyLabel banner | 2, 5 |
| limit fallback | 2, 5 |
| Help | 2, 6 |
| No Gross cap in JS | 2, 5 |
