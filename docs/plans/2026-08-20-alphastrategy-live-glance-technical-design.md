# Live Glance Book Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One live Alpaca book and one `runtime.yaml` parse per desk glance; flatten/place drop the book cache so kill then refresh is honest.

**Architecture:** Supervisor `live_book()` TTL cache for GET paths only. `_read_runtime()` stamp-caches the dict. GET risk uses `sleeve_policies`. Order/flatten paths stay on the broker.

**Tech Stack:** Supervisor, local HTTP handlers, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-live-glance-requirements.md`](../requirements/2026-08-20-alphastrategy-live-glance-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. GET status/risk must not flatten.
- Idle overlays stay unpublished.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/api/handlers.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Status, Portfolio, and Risk share one live book glance",
    "Risk overlays load runtime once per glance",
```

In `tests/alphastrategy/test_api.py` `FakeBroker.__init__` add `self.account_reads = 0` and `self.position_reads = 0`. Increment them in `get_account` / `list_positions`.

After `test_status_and_risk_include_utilization`:

```python
def test_status_portfolio_risk_share_one_live_book(api_stack) -> None:
    client, _home, _supervisor, broker = api_stack
    broker.positions = {"AAPL": 4.0}
    client.get("/api/status")
    client.get("/api/portfolio")
    client.get("/api/risk")
    assert broker.account_reads == 1
    assert broker.position_reads == 1


def test_portfolio_after_account_kill_is_not_stale_live_book(api_stack) -> None:
    client, _home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 15.0}
    before = client.get("/api/portfolio").json()
    assert any(pos.get("symbol") == "AAPL" for pos in before["positions"])
    killed = client.post("/api/paper/kill", json={})
    assert killed.status == 200
    after = client.get("/api/portfolio").json()
    assert after["positions"] == []
    assert broker.close_all_count >= 1
```

In `tests/alphastrategy/test_halt_flatten.py` after the spoken-policy cache tests:

```python
def test_sleeve_policies_read_runtime_once(tmp_path: Path) -> None:
    supervisor = _make_supervisor(
        tmp_path,
        FakeBroker(),
        evaluators={"asb_a": {"AAPL": 1.0}, "asb_b": {"MSFT": 1.0}},
    )
    reads = {"n": 0}
    inner = supervisor._read_runtime

    def counted() -> dict:
        reads["n"] += 1
        return inner()

    supervisor._read_runtime = counted  # type: ignore[method-assign]
    policies = supervisor.sleeve_policies(["asb_a", "asb_b"])
    assert set(policies) == {"asb_a", "asb_b"}
    assert reads["n"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_api.py::test_status_portfolio_risk_share_one_live_book \
  tests/alphastrategy/test_api.py::test_portfolio_after_account_kill_is_not_stale_live_book \
  tests/alphastrategy/test_halt_flatten.py::test_sleeve_policies_read_runtime_once \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL. Three GETs increment account/position reads past 1. `sleeve_policies` missing. Help phrases missing.

If the kill-then-portfolio test PASSES on RED (close_all already empties, no cache yet), keep it as a lock.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git commit -m "test: one live book per desk glance"
```

---

### Task 2: Cache + handlers + help

- [ ] **Step 1: Supervisor live_book + runtime stamp + sleeve_policies**

`import time` in `loop.py`.

In `__init__`: `self._live_book_cache = None` and `self._runtime_doc_cache = None`.

```python
    LIVE_BOOK_TTL_SEC = 1.0

    def _invalidate_live_book(self) -> None:
        self._live_book_cache = None

    def live_book(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        with self._lock:
            now = time.monotonic()
            cached = self._live_book_cache
            if cached is not None and (now - cached[0]) < self.LIVE_BOOK_TTL_SEC:
                return cached[1], cached[2]
            account = self._broker.get_account()
            positions = self._broker.list_positions()
            self._live_book_cache = (now, account, positions)
            return account, positions

    def sleeve_policies(self, bundle_ids: list[str]) -> dict[str, AccountPolicy]:
        with self._lock:
            runtime = self._read_runtime()
            return {
                bundle_id: self._effective_sleeve_policy(bundle_id, runtime)
                for bundle_id in bundle_ids
            }
```

`_read_runtime`: stamp-cache parsed dict via `_file_stamp`. `_flatten_account` first line after state notes: `_invalidate_live_book()`. `_place_batch` before each return: `_invalidate_live_book()`.

- [ ] **Step 2: from_supervisor + handlers**

`from_supervisor` live=True: `account, positions = supervisor.live_book()`.

`handle_get_portfolio`: `account, raw_positions = supervisor.live_book()` then enrich `raw_positions`.

`handle_get_risk`:

```python
    imported = _list_imported_bundles(home)
    sleeves = {
        bundle_id: _policy_to_dict(policy)
        for bundle_id, policy in supervisor.sleeve_policies(imported).items()
    }
```

Keep `_effective_sleeve_policy` in handlers unused? **Delete it** if nothing else calls it. Keep `_bundle_envelope` for PUT.

- [ ] **Step 3: Help / README**

Cockpit + `how_portfolio`: `Status, Portfolio, and Risk share one live book glance.`

`how_risk`: `Risk overlays load runtime once per glance.`

README near utilization / cockpit poll: both sentences.

- [ ] **Step 4: Targeted tests then full suite**

Expected: PASS. `test_status_live_limit_does_not_flatten` still green.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: one live book per desk glance"
```
