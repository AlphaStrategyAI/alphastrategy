# Start paper that cannot seed last weights holds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When Start paper cannot seed last sleeve weights, the desk names that health halt on Run, CLI, and POST JSON instead of the already-halted resume sentence.

**Architecture:** Prefix `_halt` on seed eval failure. POST `/api/paper/start` returns `halt_reason` when held. Run Start hint and CLI stderr branch on that prefix. Do not flatten. Keep the exact waits-for-resume copy for already-halted starts.

**Tech Stack:** Python 3.9+, pytest, cockpit JS, helptext, README.

**Requirements:** [`docs/requirements/2026-08-21-alphastrategy-seed-hold-requirements.md`](../requirements/2026-08-21-alphastrategy-seed-hold-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No live.
- Do not evaluate DSL on GET. Do not flatten on GET or on seed failure.
- Keep exact `Start paper while halted waits for resume. Resume does not catch up.`
- Keep `_HELD_START` for already-halted CLI.
- Keep `Start paper seeds last sleeve weights`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/cli/main.py`, `src/alphastrategy/web/static/js/paint-run.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_helptext.py`
- Modify: `tests/alphastrategy/test_api.py`
- Modify: `tests/alphastrategy/test_halt_flatten.py`
- Modify: `tests/alphastrategy/test_web_tokens.py`
- Modify: `tests/alphastrategy/test_cli.py`

**Interfaces:**
- Consumes: `start_sleeve` seed halt; POST `/api/paper/start`
- Produces: halt_reason prefix `start paper seeds last sleeve weights`; help phrase `Start paper that cannot seed last weights holds`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add after `Start paper seeds last sleeve weights` if present, else after `Start paper while halted waits for resume`:

```python
    "Start paper that cannot seed last weights holds",
```

In `test_halt_flatten.py` `test_start_sleeve_halts_when_sleeve_has_no_evaluator`, after `held is True`:

```python
    reason = (supervisor.snapshot.halt_reason or "").lower()
    assert "start paper seeds last sleeve weights" in reason
    assert "asb_x" in reason
```

In `test_api.py` after `test_start_while_halted_returns_held`:

```python
def test_start_paper_seed_failure_returns_held_with_halt_reason(api_stack):
    client, home, supervisor, broker = api_stack
    home.bundle_dir("asb_z").mkdir(parents=True, exist_ok=True)
    close_all_before = broker.close_all_count
    started = client.post("/api/paper/start", json={"bundle_id": "asb_z", "allocation": 0.18})
    assert started.status == 200
    body = started.json()
    assert body["ok"] is True
    assert body["held"] is True
    assert body["flattened"] is False
    reason = (body.get("halt_reason") or "").lower()
    assert "start paper seeds last sleeve weights" in reason
    assert "asb_z" in reason
    assert supervisor.snapshot.sleeves["asb_z"] == pytest.approx(0.18)
    assert not (supervisor.snapshot.last_sleeve_weights.get("asb_z") or {})
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value == "halted"
```

In `test_js_paints_run_start_hint` after the waits-for-resume assert:

```python
    assert "Start paper that cannot seed last weights holds. Resume does not catch up." in paint
    assert "start paper seeds last sleeve weights" in paint
    assert "halt_reason" in paint
```

Keep the exact waits-for-resume string assert.

In `test_cli.py` after `test_paper_start_while_halted_prints_held`:

```python
def test_paper_start_seed_failure_prints_seed_hold(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    home = AlphaStrategyHome.from_env()
    home.bundle_dir("asb_z").mkdir(parents=True, exist_ok=True)
    rc = main(["paper", "start", "--bundle", "asb_z", "--allocation", "0.18"])
    assert rc == 0
    err = capsys.readouterr().err.lower()
    assert "held:" in err
    assert "cannot seed last weights holds" in err
    assert "catch up" in err
    assert "flattened:" not in err
```

Keep `test_paper_start_while_halted_prints_held` resume / catch up.

- [ ] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_halts_when_sleeve_has_no_evaluator tests/alphastrategy/test_api.py::test_start_paper_seed_failure_returns_held_with_halt_reason tests/alphastrategy/test_api.py::test_start_while_halted_returns_held tests/alphastrategy/test_web_tokens.py::test_js_paints_run_start_hint tests/alphastrategy/test_cli.py::test_paper_start_seed_failure_prints_seed_hold tests/alphastrategy/test_cli.py::test_paper_start_while_halted_prints_held tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: seed-hold / halt_reason / hint / CLI / help fail. Already-halted locks still pass.

- [ ] **Step 3: Commit tests and docs**

```bash
git add docs/requirements/2026-08-21-alphastrategy-seed-hold-requirements.md docs/plans/2026-08-21-alphastrategy-seed-hold-technical-design.md tests/alphastrategy/test_api.py tests/alphastrategy/test_halt_flatten.py tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_cli.py tests/alphastrategy/test_helptext.py
git commit -m "test: Start paper that cannot seed last weights holds"
```

---

### Task 2: Implement

**Files:**
- Modify: `src/alphastrategy/supervisor/loop.py`
- Modify: `src/alphastrategy/api/handlers.py`
- Modify: `src/alphastrategy/cli/main.py`
- Modify: `src/alphastrategy/web/static/js/paint-run.js`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

- [ ] **Step 4: Engine / API / CLI**

`loop.py` `_seed_last_sleeve_weights` except:

```python
        except (HaltRequested, IllegalWeights) as exc:
            self._halt("start paper seeds last sleeve weights: " + str(exc))
            return
```

`handle_post_paper_start`:

```python
        held = supervisor.start_sleeve(bundle_id, allocation)
        flattened = supervisor.state in (
            SupervisorState.FLATTENING,
            SupervisorState.STOPPED,
        )
        payload = {"ok": True, "held": held, "flattened": flattened}
        if held and supervisor.snapshot.halt_reason:
            payload["halt_reason"] = supervisor.snapshot.halt_reason
        _json_response(handler, 200, payload)
```

`cli/main.py` after `_HELD_START`:

```python
_SEED_HELD_START = (
    "held: start paper that cannot seed last weights holds. Resume does not catch up."
)

def _held_start_line(halt_reason: Any) -> str:
    text = str(halt_reason or "").lower()
    if "start paper seeds last sleeve weights" in text:
        return _SEED_HELD_START
    return _HELD_START
```

Use `_held_start_line(payload.get("halt_reason"))` on the HTTP path and `_held_start_line(supervisor.snapshot.halt_reason)` on the offline path. Flatten still wins.

- [ ] **Step 5: Run Start hint**

In `renderRunStartHint`, replace the halted block with:

```javascript
    if (halted) {
      el.className = "warn";
      const reason =
        (state.status && state.status.halt_reason) ||
        (state.portfolio && state.portfolio.halt_reason) ||
        "";
      el.textContent = /start paper seeds last sleeve weights/i.test(String(reason))
        ? "Start paper that cannot seed last weights holds. Resume does not catch up."
        : "Start paper while halted waits for resume. Resume does not catch up.";
      return;
    }
```

Keep flatten / idle sentences. No `innerHTML`. File ≤ 400 lines.

- [ ] **Step 6: Help and README**

Add `Start paper that cannot seed last weights holds. ` to `execution` (after Start paper seeds last sleeve weights), `halt_flatten` (after Start paper seeds last sleeve weights), `how_run` (after Start paper seeds last sleeve weights), `task_start` (after Start paper while halted).

README Operator after Start paper seeds last sleeve weights. Keep waits-for-resume. Keep `Next rebalance`.

- [ ] **Step 7: Full suite**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

- [ ] **Step 8: Commit, push, update PR**

```bash
git add src/alphastrategy/supervisor/loop.py src/alphastrategy/api/handlers.py src/alphastrategy/cli/main.py src/alphastrategy/web/static/js/paint-run.js src/alphastrategy/helptext.py README.md
git commit -m "feat: Start paper that cannot seed last weights holds"
```
