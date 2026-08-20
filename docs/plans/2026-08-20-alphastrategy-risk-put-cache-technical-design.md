# Risk PUT Supervisor cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PUT `/api/risk` plans, persists, and flatten-now through Supervisor digest-cached runtime/envelope reads.

**Architecture:** `Supervisor.apply_risk` deep-copies `_read_runtime()`, validates with `_bundle_envelope`, writes `runtime.yaml` via `replace_text`, then `_enforce_live_book`. `handle_put_risk` is a JSON wrapper.

**Tech Stack:** Python 3.9+, PyYAML, persist.replace_text, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-risk-put-cache-requirements.md`](../requirements/2026-08-20-alphastrategy-risk-put-cache-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- Heartbeat does not flatten. GET status/risk must not flatten.
- Do not feed `plan_orders` from `live_book()`.
- Idle overlays stay unpublished until allocation > 0.
- Flatten-now uses the Book live book.
- `runtime.yaml` persist stays `replace_text` (no `write_text`).
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/helptext.py`, `README.md`, `tests/alphastrategy/test_persist.py`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_persist.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Tighten PUT reads runtime overlays from the Supervisor",
```

In `tests/alphastrategy/test_api.py` after `test_put_risk_tightens_account_policy`:

```python
def test_put_risk_source_uses_supervisor_apply_risk() -> None:
    from alphastrategy.api import handlers as handlers_mod

    src = Path(handlers_mod.__file__).read_text(encoding="utf-8")
    body = src.split("def handle_put_risk", 1)[1].split("def dispatch", 1)[0]
    assert "apply_risk" in body
    assert "_load_runtime" not in body
    assert "_bundle_envelope" not in body


def test_put_risk_overlay_does_not_reload_envelope_in_handlers(
    api_stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alphastrategy.api import handlers as handlers_mod

    client, home, supervisor, _broker = api_stack
    bundle_dir = home.imported_dir() / "asb_x"
    (bundle_dir / "risk-envelope.yaml").write_text(
        "max_name_weight: 0.20\n", encoding="utf-8"
    )
    loads = {"n": 0}
    orig = handlers_mod.load_risk_envelope

    def counted(raw: bytes):
        loads["n"] += 1
        return orig(raw)

    monkeypatch.setattr(handlers_mod, "load_risk_envelope", counted)
    supervisor.sleeve_policies(["asb_x"])
    response = client.put(
        "/api/risk",
        json={"sleeves": {"asb_x": {"max_name_weight": 0.15}}},
    )
    assert response.status == 200
    assert response.json()["ok"] is True
    assert loads["n"] == 0
```

In `tests/alphastrategy/test_persist.py` keep `replace_text` / no `write_text`, but follow Supervisor if the write moves:

```python
def test_save_runtime_source_uses_replace_text() -> None:
    from alphastrategy.supervisor import loop as loop_mod

    src = Path(loop_mod.__file__).read_text(encoding="utf-8")
    body = src.split("def _write_runtime", 1)[1].split("def ", 1)[0]
    assert "replace_text" in body
    assert "write_text" not in body
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases \
  tests/alphastrategy/test_api.py::test_put_risk_source_uses_supervisor_apply_risk \
  tests/alphastrategy/test_api.py::test_put_risk_overlay_does_not_reload_envelope_in_handlers \
  tests/alphastrategy/test_persist.py::test_save_runtime_source_uses_replace_text \
  -q
```

Expected: FAIL (phrase missing; `apply_risk` missing; handlers envelope load count > 0; persist still looks at handlers `_save_runtime` until the test change, then `_write_runtime` missing).

- [ ] **Step 3: Commit failing tests and docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-risk-put-cache-requirements.md \
  docs/plans/2026-08-20-alphastrategy-risk-put-cache-technical-design.md \
  tests/alphastrategy/test_helptext.py tests/alphastrategy/test_api.py \
  tests/alphastrategy/test_persist.py
git commit -m "test: Tighten PUT reads runtime overlays from the Supervisor"
```

---

### Task 2: Engine + help

- [ ] **Step 1: `apply_risk` + `_write_runtime`**

In `src/alphastrategy/supervisor/loop.py` add `import copy` and `from alphastrategy.persist import discard_stale, replace_text`. After `_read_runtime`:

```python
    def _write_runtime(self, runtime: dict[str, Any]) -> None:
        path = self._home.runtime_path()
        replace_text(
            path,
            yaml.safe_dump(runtime, sort_keys=True),
            prefix=".runtime.",
        )

    def apply_risk(
        self,
        account_patch: dict[str, Any] | None,
        sleeves_patch: dict[str, Any] | None,
    ) -> bool:
        with self._lock:
            if account_patch is not None and not isinstance(account_patch, dict):
                raise ValueError("account must be an object")
            if sleeves_patch is not None and not isinstance(sleeves_patch, dict):
                raise ValueError("sleeves must be an object")
            runtime = copy.deepcopy(self._read_runtime())
            account_overlay = runtime.get("account_overlay", {})
            if not isinstance(account_overlay, dict):
                account_overlay = {}
            sleeve_overlays = runtime.get("sleeve_overlays", {})
            if not isinstance(sleeve_overlays, dict):
                sleeve_overlays = {}
            planned_account_overlay = dict(account_overlay)
            planned_sleeve_overlays = {
                bundle_id: dict(overlay)
                for bundle_id, overlay in sleeve_overlays.items()
                if isinstance(overlay, dict)
            }
            projected_policy = self._policy
            if account_patch is not None:
                projected_policy = merge_limits({}, self._policy, account_patch)
                planned_account_overlay.update(account_patch)
            if sleeves_patch is not None:
                for bundle_id, patch in sleeves_patch.items():
                    if not isinstance(patch, dict):
                        raise ValueError(
                            f"sleeve overlay for {bundle_id} must be an object"
                        )
                    envelope = self._bundle_envelope(bundle_id)
                    stored = planned_sleeve_overlays.get(bundle_id, {})
                    current_effective = merge_limits(envelope, projected_policy, stored)
                    merge_limits({}, current_effective, patch)
                    stored.update(patch)
                    planned_sleeve_overlays[bundle_id] = stored
            if account_patch is not None:
                self._policy = merge_limits({}, self._policy, account_patch)
                self._enforce_live_book()
                runtime["account_overlay"] = planned_account_overlay
            if sleeves_patch is not None:
                runtime["sleeve_overlays"] = planned_sleeve_overlays
            if account_patch is not None or sleeves_patch is not None:
                self._write_runtime(runtime)
                if sleeves_patch is not None:
                    self._enforce_live_book()
            return self._snapshot.state in (
                SupervisorState.FLATTENING,
                SupervisorState.STOPPED,
            )
```

`handle_put_risk`:

```python
        body = _read_json_body(handler)
        flattened = supervisor.apply_risk(body.get("account"), body.get("sleeves"))
        _json_response(handler, 200, {"ok": True, "flattened": flattened})
```

Keep the `ImportRejected` / `ValueError` handlers. Delete `_load_runtime` and `_bundle_envelope`. `_apply_startup_runtime` uses `supervisor._read_runtime()`. Delete `_save_runtime` after persist lock moves. Drop unused `yaml` / `load_risk_envelope` / `merge_limits` / `replace_text` imports from handlers if nothing else needs them.

- [ ] **Step 2: Help and README**

Insert `Tighten PUT reads runtime overlays from the Supervisor. ` after `Runtime overlays load once until the file changes. ` in `execution`, `how_risk`, and after `Tighten that breaches the live book flattens now. ` in `halt_flatten` and `task_tighten`. README Operator after the runtime-overlays sentence.

- [ ] **Step 3: Run the new tests plus existing PUT flatten locks**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases \
  tests/alphastrategy/test_api.py::test_put_risk_source_uses_supervisor_apply_risk \
  tests/alphastrategy/test_api.py::test_put_risk_overlay_does_not_reload_envelope_in_handlers \
  tests/alphastrategy/test_api.py::test_put_risk_tightens_account_policy \
  tests/alphastrategy/test_api.py::test_put_risk_flattens_when_live_book_breaches \
  tests/alphastrategy/test_api.py::test_put_risk_overlay_while_idle_does_not_flatten_live_book \
  tests/alphastrategy/test_api.py::test_put_risk_overlay_while_allocated_flattens_live_book \
  tests/alphastrategy/test_persist.py::test_save_runtime_source_uses_replace_text \
  tests/alphastrategy/test_halt_flatten.py::test_spoken_policy_sees_runtime_yaml_write \
  -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/alphastrategy/supervisor/loop.py src/alphastrategy/api/handlers.py \
  src/alphastrategy/helptext.py README.md
git commit -m "feat: Tighten PUT reads runtime overlays from the Supervisor"
```

---

### Task 3: Full suite

- [ ] **Step 1: Run**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

Expected: all passed.

## Spec coverage

| Requirement | Task |
| --- | --- |
| PUT uses apply_risk, not handlers parsers | 1–2 |
| Envelope cache reused | 1 |
| replace_text persist | 1–2 |
| Help phrase | 1–2 |
| Existing flatten / spoken digest locks | 2–3 |
