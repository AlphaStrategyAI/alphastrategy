# Flatten-Next Clock and Start Hint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clock Next reads `flatten ·` with warn while `live_limit` is set; Run Start hint names the breached cap after a flatten; both paper-start POSTs read `flattened`.

**Architecture:** Paint-only on countdown (no JSON change). Run hint uses existing `last_kill`. Start handlers keep the POST body.

**Tech Stack:** Quiet cockpit JS, helptext, README, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-flatten-next-requirements.md`](../requirements/2026-08-20-alphastrategy-flatten-next-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. Keep `held ·` and `flat ·`.
- Each `js/` part stays ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/js/paint-run.js`, `src/alphastrategy/web/static/js/boot.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Clock Next is flatten while the live book is through the spoken cap",
    "Start paper that flattens names the breached cap",
```

In `tests/alphastrategy/test_web_tokens.py` after `test_js_clock_next_flat_while_flattened`:

```python
def test_js_clock_next_flatten_while_live_limit(js_text: str) -> None:
    session = js_text[
        js_text.find("function renderSessionMetrics") : js_text.find("function bookDrift")
    ]
    assert "flatten · " in session
    assert "live_limit" in session
    assert 'countEl.classList.add("warn")' in session
    assert "held · " in session
    assert "flat · " in session
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
```

Extend `test_js_paints_run_start_hint` (keep existing restart sentence) with:

```python
    assert "last_kill" in paint
    assert "policyLabel" in paint
    assert "flattened the paper account" in paint
```

After `test_js_paints_run_start_hint` add:

```python
def test_js_start_posts_read_flattened(js_text: str) -> None:
    boot = js_text[
        js_text.find("async function onStartSubmit") : js_text.find(
            "async function onRiskAccountSubmit"
        )
    ]
    assert ".flattened" in boot
    sleeves = js_text[
        js_text.find("function renderRunSleeves") : js_text.find("function renderRunStartHint")
    ]
    assert ".flattened" in sleeves
    assert "window.confirm" not in js_text
    assert "Gross cap" not in js_text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_web_tokens.py::test_js_clock_next_flatten_while_live_limit \
  tests/alphastrategy/test_web_tokens.py::test_js_paints_run_start_hint \
  tests/alphastrategy/test_web_tokens.py::test_js_start_posts_read_flattened \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL. Clock lacks `flatten ·`. Hint lacks `last_kill`. Start POSTs lack `.flattened`. Help phrases missing.

If `test_js_paints_run_start_hint` fails only on the new asserts, keep the existing restart sentence.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-flatten-next-requirements.md \
  docs/plans/2026-08-20-alphastrategy-flatten-next-technical-design.md \
  tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_helptext.py
git commit -m "test: Clock Next flatten pending; Start names the breached cap"
```

---

### Task 2: Paint + help

- [ ] **Step 1: Clock Next**

In `renderSessionMetrics`, after the flattened branch, before the else that sets `kindEl.textContent = kind`:

```javascript
      } else if (
        utilization().live_limit &&
        utilization().live_limit.reason
      ) {
        countEl.classList.add("warn");
        kindEl.textContent = "flatten · " + kind;
      } else {
        kindEl.textContent = kind;
      }
```

- [ ] **Step 2: Run start hint + POST**

`renderRunStartHint` flattened branch:

```javascript
    if (flattened) {
      el.className = "fail";
      const kill = state.status && state.status.last_kill;
      const killReason = kill && kill.reason;
      const capFlat =
        killReason === "long_only" ||
        (killReason && NUMERIC_CAPS.indexOf(killReason) !== -1);
      const restart =
        "Start paper after flatten starts the session loop again and does not catch up.";
      el.textContent = capFlat
        ? policyLabel(killReason) + " flattened the paper account. " + restart
        : restart;
      return;
    }
```

Sleeve start POST in `paint-run.js`:

```javascript
          const started = await api("POST", "/api/paper/start", {
            bundle_id: bundleId,
            allocation,
          });
          void (started && started.flattened);
          void (started && started.held);
```

(`void` is fine; reading the fields is the contract. Prefer using them only to satisfy the test with `started.flattened` / `started.held` in the expression — e.g. keep refresh either way.)

`onStartSubmit` in `boot.js`: same `const started = await api(...)` and read `.flattened` / `.held` before `refresh()`.

- [ ] **Step 3: Help / README**

`how_portfolio` after flat Next: `Clock Next is flatten while the live book is through the spoken cap.`

`how_run` after overlay flatten: `Start paper that flattens names the breached cap.`

README Clock line: Next is flatten while the live book is through the spoken cap.

- [ ] **Step 4: Targeted tests then full suite**

Expected: PASS. JS parts ≤ 400 lines.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: Clock Next flatten pending; Start names the breached cap"
```
