# Activity Kill Blotter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (this cycle explicitly chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show isolated vs flattened on Activity kill rows, and include `last_kill` on offline CLI `status`.

**Architecture:** Scan-line copy lives in Quiet-cockpit `eventSummary`. Offline status copies `snapshot.last_kill` into the same JSON key the control plane already uses. No Supervisor kill-path change.

**Tech Stack:** Existing static JS, CLI status, pytest. Broker mocked.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-activity-kill-blotter-requirements.md`](../requirements/2026-08-20-alphastrategy-activity-kill-blotter-requirements.md)

## Global Constraints

- Package `alphastrategy`, paper-only walls unchanged.
- Do not grow `src/openstrategy/`.
- Do not change isolation math.
- Five `#nav` screens. No `window.confirm`.
- Do not rewrite audit JSONL schema.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never place a real order.

## File map

- Modify: `src/alphastrategy/web/static/app.js` — `eventSummary` kill branch
- Modify: `src/alphastrategy/cli/main.py` — offline `_cmd_status` includes `last_kill`
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`
- Test: `tests/alphastrategy/test_cli.py`
- Test: `tests/alphastrategy/test_helptext.py`

---

### Task 1: Activity kill scan text

**Files:**
- Modify: `src/alphastrategy/web/static/app.js`
- Test: `tests/alphastrategy/test_web_tokens.py`

**Interfaces:**
- Consumes: audit `kill` events with `isolated` and/or `scope`
- Produces: scan text `isolated residual` / `flattened account`

- [ ] **Step 1: Write the failing test**

Append to `tests/alphastrategy/test_web_tokens.py`:

```python
def test_js_activity_kill_summary_distinguishes_isolated(js_text: str) -> None:
    kill_branch = js_text.split('case "kill":')[1].split("case \"flatten\":")[0]
    assert "isolated residual" in kill_branch
    assert "flattened account" in kill_branch
    assert "ev.isolated" in kill_branch
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_activity_kill_summary_distinguishes_isolated -q`

Expected: FAIL — `case "kill":` exists but the split is shared with `paper_start` (`case "kill":` follows import). If the split is empty or lacks the phrases, the assert fails.

Note: `eventSummary` currently groups `paper_start` / `paper_stop` / `import` / `kill` in one case. After the change, `kill` is its own case. The test splits on `case "kill":`.

- [ ] **Step 3: Write minimal implementation**

In `src/alphastrategy/web/static/app.js`, replace the grouped case so `kill` is separate:

```javascript
      case "paper_start":
      case "paper_stop":
      case "import":
        return ev.bundle_id || ev.scope || "";
      case "kill": {
        const id = ev.bundle_id || "";
        if (ev.isolated === true) {
          return `isolated residual ${id}`.trim();
        }
        if (ev.isolated === false || ev.scope === "account") {
          return `flattened account ${id}`.trim();
        }
        return id || ev.scope || "";
      }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py -q`

Expected: PASS. Five nav screens still exact.

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/web/static/app.js tests/alphastrategy/test_web_tokens.py
git commit -m "feat: Activity kill rows say isolated residual vs flattened"
```

---

### Task 2: Offline CLI status last_kill

**Files:**
- Modify: `src/alphastrategy/cli/main.py`
- Test: `tests/alphastrategy/test_cli.py`

**Interfaces:**
- Consumes: `SupervisorSnapshot.last_kill`
- Produces: offline `status` JSON key `last_kill`

- [ ] **Step 1: Write the failing tests**

In `test_status_prints_json`, after the existing asserts, add:

```python
    assert "last_kill" in payload
    assert payload["last_kill"] is None
```

Append:

```python
def test_offline_status_includes_last_kill_after_account_kill(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    _create_imported_bundle(cli_home)
    assert main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"]) == 0
    assert main(["paper", "kill", "--force"]) == 0
    capsys.readouterr()
    rc = main(["status"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["last_kill"]["reason"] == "account"
    assert payload["last_kill"]["flattened"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_cli.py::test_status_prints_json tests/alphastrategy/test_cli.py::test_offline_status_includes_last_kill_after_account_kill -q`

Expected: FAIL — `last_kill` missing from offline status JSON.

- [ ] **Step 3: Write minimal implementation**

In `_cmd_status` offline payload, add `"last_kill": snapshot.last_kill`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_cli.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/cli/main.py tests/alphastrategy/test_cli.py
git commit -m "feat: include last_kill on offline CLI status"
```

---

### Task 3: Help and README

**Files:**
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`
- Test: `tests/alphastrategy/test_helptext.py`

**Interfaces:**
- Produces: help mentions Activity isolated residual / flattened account

- [ ] **Step 1: Write the failing test**

Add `"isolated residual"` to `REQUIRED_PHRASES` in `test_helptext.py` (lowercase match via `.lower()`).

```python
REQUIRED_PHRASES = (
    "halt is not flatten",
    "paper only",
    "sole order placer",
    "does not catch up",
    "FLATTEN",
    "--force",
    "isolated residual",
    "Wanted",
    "Got",
)
```

The existing loop already lowercases non-special phrases, so `"isolated residual"` matches `text.lower()`.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

Expected: FAIL — phrase missing.

- [ ] **Step 3: Write minimal copy**

In `helptext.py` `cockpit` body, after the FLAT banner sentence, add:

```text
 Activity kill rows say isolated residual or flattened account. status includes last_kill even when the control plane is down.
```

In README Operator, after the sleeve-kill JSON/banner bullet, add:

```markdown
- Activity kill rows say **isolated residual** or **flattened account**.
  `alphastrategy status` includes `last_kill` even if the desk is down.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_cli.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/helptext.py README.md tests/alphastrategy/test_helptext.py
git commit -m "docs: Activity kill rows and offline last_kill"
```

---

### Task 4: Full suite

- [ ] **Step 1:** `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all pass. No real broker.

- [ ] **Step 2:** Commit only if anything was fixed.

---

## Self-review

| Spec item | Task |
| --- | --- |
| Activity isolated residual / flattened account | 1 |
| Offline status last_kill | 2 |
| Help/README | 3 |
| No audit schema rewrite | 1 uses existing `isolated` / `scope` |
| No isolation math / sixth screen | file map |
