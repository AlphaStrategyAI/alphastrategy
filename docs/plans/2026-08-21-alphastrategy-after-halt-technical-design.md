# After halt is four tiles Reason / Spent / Next / Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn After halt into a four-tile glance (Reason / Spent / Next / Resume) so halt, spent, held, and wait are instruments on Run.

**Architecture:** HTML metrics-4 in `#run-recover`. `renderRunRecover` paints status fields and `formatHaltBanner`. Keep `#account-resume`. Do not change supervisor/API. Reason hero wraps at 1.15rem.

**Tech Stack:** Python 3.9+, pytest, cockpit HTML/CSS/JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-after-halt-requirements.md`](../requirements/2026-08-21-alphastrategy-after-halt-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET.
- Keep exact Start hint sentences.
- Keep `renderBanners` a single `const reason`.
- `paint-portfolio.js` and `paint-rails.js` stay ≤ 400 lines. This increment lives in `index.html`, `styles.css`, `paint-run.js`.
- Keep `#run-halt-reason` and `#account-resume`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/web/static/js/paint-run.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_web_tokens.py`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add after `HALT names Start paper that cannot seed last weights holds`:

```python
    "After halt is four tiles Reason / Spent / Next / Resume",
```

In `test_html_run_kill_switch_zones`, after `id="run-halt-reason"` in recover:

```python
    assert "metrics-4" in recover
    assert ">Reason<" in recover
    assert ">Spent<" in recover
    assert ">Next<" in recover
    assert ">Resume<" in recover
    assert 'id="run-halt-spent"' in recover
    assert 'id="run-halt-next"' in recover
    assert 'id="run-halt-resume"' in recover
    assert 'id="run-halt-hint"' in recover
    assert 'id="run-halt-reason-sub"' in recover
```

Keep `id="account-resume"` in recover. Keep five `#nav` screens.

In `test_js_paints_run_halt_reason` after the seed-hold sentence assert:

```python
    assert "run-halt-spent" in paint
    assert "run-halt-next" in paint
    assert "run-halt-resume" in paint
    assert "run-halt-hint" in paint
    assert "run-halt-reason-sub" in paint
    assert "formatHaltBanner" in paint
    assert '"spent"' in paint or "spent" in paint
    assert '"held"' in paint
    assert '"wait"' in paint
```

Keep `Resume is only after halt.` Keep `innerHTML` not in paint. Keep `test_js_paints_run_start_hint`.

New CSS test after `test_css_run_halt_reason` if present, else after `test_css_run_kill_switch_zones`:

```python
def test_css_after_halt_tiles(css_text: str) -> None:
    hero = re.search(
        r"#run-recover\s+\.metric\.hero\s+\.metric-value\s*\{[^}]*\}",
        css_text,
    )
    assert hero is not None and "1.15rem" in hero.group(0)
    for sel in (
        "#run-halt-reason.warn",
        "#run-halt-spent.warn",
        "#run-halt-next.warn",
        "#run-halt-resume.warn",
    ):
        block = re.search(re.escape(sel) + r"\s*\{[^}]*\}", css_text)
        assert block is not None and "#f59e0b" in block.group(0).lower()
```

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_run_kill_switch_zones tests/alphastrategy/test_web_tokens.py::test_js_paints_run_halt_reason tests/alphastrategy/test_web_tokens.py::test_js_paints_run_start_hint tests/alphastrategy/test_web_tokens.py::test_css_after_halt_tiles tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: HTML tiles / recover paint / CSS / help fail. Start hint lock still passes.

- [ ] **Step 3: Commit tests and docs**

```bash
git add docs/requirements/2026-08-21-alphastrategy-after-halt-requirements.md docs/plans/2026-08-21-alphastrategy-after-halt-technical-design.md tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_helptext.py
git commit -m "test: After halt is four tiles Reason / Spent / Next / Resume"
```

---

### Task 2: Implement

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`
- Modify: `src/alphastrategy/web/static/styles.css`
- Modify: `src/alphastrategy/web/static/js/paint-run.js`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

- [ ] **Step 4: HTML / CSS / paint**

Replace the After halt panel body (keep heading) with metrics-4 then hint then panel with the Resume button and error box. Exact ids from the requirements table. Reason is `.metric.hero`. Empty colspan unchanged elsewhere.

`renderRunRecover` paints all four tiles + sub + hint per the requirements table. No `innerHTML`. File ≤ 400 lines.

CSS as specified. Keep `#run-halt-reason.warn`. Do not change Quiet tokens.

- [ ] **Step 5: Help and README**

Add `After halt is four tiles Reason / Spent / Next / Resume. ` to `cockpit`, `how_run`, `halt_flatten` as specified. README Operator after HALT names…. Keep `Next rebalance`.

- [ ] **Step 6: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 7: Commit, push, update PR**

```bash
git add src/alphastrategy/web/static/index.html src/alphastrategy/web/static/styles.css src/alphastrategy/web/static/js/paint-run.js src/alphastrategy/helptext.py README.md
git commit -m "feat: After halt is four tiles Reason / Spent / Next / Resume"
```
