# Heartbeat Sticky Live-Book Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A heartbeat-seeded `live_book()` holds until flatten or place; glance-only fetches still expire after 1s.

**Architecture:** `_live_book_cache` becomes `(monotonic, account, positions, sticky)`. Heartbeat stores `sticky=True`. `live_book()` returns a sticky pair without consulting TTL. Glance misses store `sticky=False` and keep `LIVE_BOOK_TTL_SEC`. Invalidate still clears the cache. Order paths still hit the broker.

**Tech Stack:** Supervisor, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-sticky-book-requirements.md`](../requirements/2026-08-20-alphastrategy-sticky-book-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. GET status/risk must not flatten.
- Do not use `live_book()` inside `_equity()` / `_enforce_live_book`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "A heartbeat live book holds until flatten or place",
```

In `tests/alphastrategy/test_api.py` after `test_tick_seeds_live_book_for_status_and_portfolio`:

```python
def test_glance_live_book_expires_after_ttl(api_stack, monkeypatch: pytest.MonkeyPatch) -> None:
    from alphastrategy.supervisor import loop as loop_mod
    from alphastrategy.supervisor.loop import Supervisor

    client, _home, _supervisor, broker = api_stack
    broker.positions = {"AAPL": 4.0}
    clock = {"t": 0.0}
    monkeypatch.setattr(loop_mod.time, "monotonic", lambda: clock["t"])
    client.get("/api/status")
    assert broker.account_reads == 1
    assert broker.position_reads == 1
    clock["t"] += Supervisor.LIVE_BOOK_TTL_SEC + 0.1
    client.get("/api/status")
    assert broker.account_reads == 2
    assert broker.position_reads == 2


def test_heartbeat_live_book_holds_past_ttl_for_status_and_portfolio(
    api_stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alphastrategy.supervisor import loop as loop_mod
    from alphastrategy.supervisor.loop import Supervisor

    client, _home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 4.0}
    clock = {"t": 0.0}
    monkeypatch.setattr(loop_mod.time, "monotonic", lambda: clock["t"])
    supervisor.tick()
    accounts = broker.account_reads
    positions = broker.position_reads
    clock["t"] += Supervisor.LIVE_BOOK_TTL_SEC + 5.0
    client.get("/api/status")
    client.get("/api/portfolio")
    assert broker.account_reads == accounts
    assert broker.position_reads == positions
```

In `tests/alphastrategy/test_halt_flatten.py` after `test_heartbeat_live_book_survives_slow_price_fetch`:

```python
def test_heartbeat_live_book_holds_past_ttl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alphastrategy.supervisor import loop as loop_mod

    open_time, _session_close, broker, supervisor = _open_then_idle(tmp_path)
    broker.advance_now(open_time + timedelta(minutes=10))
    clock = {"t": 0.0}
    monkeypatch.setattr(loop_mod.time, "monotonic", lambda: clock["t"])
    accounts = {"n": 0}
    positions = {"n": 0}
    inner_account = broker.get_account
    inner_positions = broker.list_positions

    def counted_account() -> dict:
        accounts["n"] += 1
        return inner_account()

    def counted_positions() -> list:
        positions["n"] += 1
        return inner_positions()

    broker.get_account = counted_account  # type: ignore[method-assign]
    broker.list_positions = counted_positions  # type: ignore[method-assign]
    supervisor.tick()
    after_tick_accounts = accounts["n"]
    after_tick_positions = positions["n"]
    clock["t"] += Supervisor.LIVE_BOOK_TTL_SEC + 5.0
    supervisor.live_book()
    assert accounts["n"] == after_tick_accounts
    assert positions["n"] == after_tick_positions
    assert after_tick_accounts >= 1
    assert after_tick_positions >= 1
```

If `test_api.py` does not already import `pytest`, add `import pytest`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_api.py::test_glance_live_book_expires_after_ttl \
  tests/alphastrategy/test_api.py::test_heartbeat_live_book_holds_past_ttl_for_status_and_portfolio \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_live_book_holds_past_ttl \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL. Heartbeat seed expires after TTL so GET/`live_book` extra-reads. Help phrase missing.

`test_glance_live_book_expires_after_ttl` should PASS on RED (glance 1s TTL already exists). Keep it as a lock.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git commit -m "test: heartbeat live book holds past glance TTL"
```

---

### Task 2: Engine + help

- [ ] **Step 1: Sticky cache tuple**

In `__init__` change the cache type to `tuple[float, dict[str, Any], list[dict[str, Any]], bool] | None`.

```python
    def live_book(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        with self._lock:
            now = time.monotonic()
            cached = self._live_book_cache
            if cached is not None and (
                cached[3] or (now - cached[0]) < self.LIVE_BOOK_TTL_SEC
            ):
                return cached[1], cached[2]
            account = self._broker.get_account()
            positions = self._broker.list_positions()
            self._live_book_cache = (now, account, positions, False)
            return account, positions

    def _invalidate_live_book(self) -> None:
        self._live_book_cache = None

    def _touch_live_book_cache(self) -> None:
        cached = self._live_book_cache
        if cached is None:
            return
        self._live_book_cache = (time.monotonic(), cached[1], cached[2], cached[3])
```

Heartbeat `finally`:

```python
        finally:
            self._live_book_cache = (time.monotonic(), account, raw_positions, True)
```

- [ ] **Step 2: Help / README**

Execution after heartbeat seeds: `A heartbeat live book holds until flatten or place.`

`how_portfolio` after share one live book: same sentence.

`how_activity` after heartbeat seeds: same sentence.

README heartbeat bullet: the new sentence after seeds.

- [ ] **Step 3: Targeted tests then full suite**

Keep `test_heartbeat_refreshes_last_prices_without_flattening`.
Keep `test_portfolio_after_account_kill_is_not_stale_live_book`.
Keep `test_heartbeat_live_book_survives_slow_price_fetch`.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: hold heartbeat live book until flatten or place"
```
