# Spoken Policy Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `spoken_policy()` / `_rebalance_policy` reuse one merge until runtime overlays, allocated envelopes, allocations, or account `_policy` change.

**Architecture:** Stamp-keyed cache on Supervisor. One `_read_runtime()` per miss. Idle allocation still unpublished.

**Tech Stack:** Supervisor, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-spoken-cache-requirements.md`](../requirements/2026-08-20-alphastrategy-spoken-cache-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. GET status/risk must not flatten.
- Idle overlays stay unpublished.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add `"Spoken policy is reused until overlays or allocations change"`.

In `tests/alphastrategy/test_halt_flatten.py` after `test_start_sleeve_without_overlay_does_not_flatten_live_book_inside_name_cap`:

```python
def test_spoken_policy_reads_runtime_once_while_unchanged(tmp_path: Path) -> None:
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    home = AlphaStrategyHome(root=tmp_path)
    (home.bundle_dir("asb_test") / "risk-envelope.yaml").write_text(
        "max_name_weight: 0.20\n", encoding="utf-8"
    )
    home.runtime_path().write_text(
        yaml.safe_dump({"sleeve_overlays": {"asb_test": {"max_name_weight": 0.05}}}),
        encoding="utf-8",
    )
    supervisor.start_sleeve("asb_test", 0.25)
    reads = {"n": 0}
    inner = supervisor._read_runtime

    def counted() -> dict:
        reads["n"] += 1
        return inner()

    supervisor._read_runtime = counted  # type: ignore[method-assign]
    first = supervisor.spoken_policy()
    second = supervisor.spoken_policy()
    assert first.max_name_weight == pytest.approx(0.05)
    assert second.max_name_weight == pytest.approx(0.05)
    assert reads["n"] == 1


def test_spoken_policy_sees_runtime_yaml_write(tmp_path: Path) -> None:
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    home = AlphaStrategyHome(root=tmp_path)
    (home.bundle_dir("asb_test") / "risk-envelope.yaml").write_text(
        "max_name_weight: 0.20\n", encoding="utf-8"
    )
    home.runtime_path().write_text(
        yaml.safe_dump({"sleeve_overlays": {"asb_test": {"max_name_weight": 0.10}}}),
        encoding="utf-8",
    )
    supervisor.start_sleeve("asb_test", 0.25)
    assert supervisor.spoken_policy().max_name_weight == pytest.approx(0.10)
    home.runtime_path().write_text(
        yaml.safe_dump({"sleeve_overlays": {"asb_test": {"max_name_weight": 0.05}}}),
        encoding="utf-8",
    )
    assert supervisor.spoken_policy().max_name_weight == pytest.approx(0.05)


def test_spoken_policy_idle_overlay_unpublished_after_stop(tmp_path: Path) -> None:
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    home = AlphaStrategyHome(root=tmp_path)
    (home.bundle_dir("asb_test") / "risk-envelope.yaml").write_text(
        "max_name_weight: 0.20\n", encoding="utf-8"
    )
    home.runtime_path().write_text(
        yaml.safe_dump({"sleeve_overlays": {"asb_test": {"max_name_weight": 0.05}}}),
        encoding="utf-8",
    )
    supervisor.start_sleeve("asb_test", 0.25)
    assert supervisor.spoken_policy().max_name_weight == pytest.approx(0.05)
    supervisor.stop_sleeve("asb_test")
    assert supervisor.spoken_policy().max_name_weight == pytest.approx(
        AccountPolicy.defaults().max_name_weight
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_halt_flatten.py::test_spoken_policy_reads_runtime_once_while_unchanged \
  tests/alphastrategy/test_halt_flatten.py::test_spoken_policy_sees_runtime_yaml_write \
  tests/alphastrategy/test_halt_flatten.py::test_spoken_policy_idle_overlay_unpublished_after_stop \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL. Unchanged pair reads runtime more than once. Help phrase missing.

If `test_spoken_policy_sees_runtime_yaml_write` or idle-after-stop PASSES on RED (current behavior already correct), keep them as locks.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git commit -m "test: spoken policy reused until overlays or allocations change"
```

---

### Task 2: Cache + help

- [ ] **Step 1: Stamp cache in Supervisor**

In `__init__` after recover hooks: `self._spoken_cache: tuple[tuple, AccountPolicy] | None = None`

Helpers (inside the class):

```python
    def _file_stamp(self, path: Path) -> tuple[int, int]:
        if not path.is_file():
            return (0, 0)
        stat = path.stat()
        return (int(stat.st_mtime_ns), int(stat.st_size))

    def _spoken_cache_key(self) -> tuple:
        allocated = tuple(
            sorted(
                (bundle_id, float(allocation))
                for bundle_id, allocation in self._snapshot.sleeves.items()
                if float(allocation) > 0
            )
        )
        envelopes = tuple(
            (bundle_id, self._file_stamp(self._home.bundle_dir(bundle_id) / "risk-envelope.yaml"))
            for bundle_id, _allocation in allocated
        )
        return (
            self._file_stamp(self._home.runtime_path()),
            envelopes,
            allocated,
            self._policy,
        )
```

`_effective_sleeve_policy(self, bundle_id: str, runtime: dict[str, Any] | None = None)` uses `runtime if runtime is not None else self._read_runtime()`.

`_rebalance_policy`:

```python
    def _rebalance_policy(self) -> AccountPolicy:
        key = self._spoken_cache_key()
        cached = self._spoken_cache
        if cached is not None and cached[0] == key:
            return cached[1]
        runtime = self._read_runtime()
        policy = self._policy
        for bundle_id, allocation in self._snapshot.sleeves.items():
            if allocation <= 0:
                continue
            policy = tighten_policy(policy, self._effective_sleeve_policy(bundle_id, runtime))
        self._spoken_cache = (key, policy)
        return policy
```

`spoken_policy` still `with self._lock: return self._rebalance_policy()`.

- [ ] **Step 2: Help / README**

Cockpit + `how_risk`: `Spoken policy is reused until overlays or allocations change.`

README near Caps / spoken: same sentence.

- [ ] **Step 3: Targeted tests then full suite**

Expected: PASS. Existing overlay flatten and GET live_limit tests still pass.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: reuse spoken policy until overlays or allocations change"
```
