# Book-enforce flatten-now Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Operator flatten-now (Tighten, Start paper, allocated overlay PUT) checks the same live book as Book/Caps; rebalance still checks the account/positions this event already fetched.

**Architecture:** Unlock the `live_book()` cache lookup. `_enforce_live_book` uses that helper unless `_rebalance` passes the pair it just fetched. `_live_book_weights` takes raw positions. Order sizing still does not read the glance cache.

**Tech Stack:** Python 3.9+, pytest, helptext, README. No JS paint change required.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-book-enforce-requirements.md`](../requirements/2026-08-20-alphastrategy-book-enforce-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. GET status/risk must not flatten.
- Do not feed `plan_orders` / `_place_batch` from `live_book()`.
- Idle overlays stay unpublished until allocation > 0.
- Each file in `JS_PARTS` stays ≤ 400 newlines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.
- Fixture: 15 AAPL × $100 / $10k = 0.15. Do not use 40 shares against the default 20% name cap.

## File map

- Modify: `src/alphastrategy/supervisor/loop.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_halt_flatten.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

**Files:**
- Modify: `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_halt_flatten.py`

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Tighten and Start paper flatten the same live book as Book",
```

In `tests/alphastrategy/test_halt_flatten.py` after `test_start_sleeve_without_overlay_does_not_flatten_live_book_inside_name_cap`:

```python
def test_set_policy_flattens_sticky_book_not_mutated_broker(tmp_path: Path) -> None:
    open_time, _session_close, broker, supervisor = _open_then_idle(tmp_path)
    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()
    assert supervisor.live_book_source() == "heartbeat"
    assert broker.positions.get("AAPL") == pytest.approx(15.0)
    broker.positions = {"AAPL": 5.0}
    supervisor.set_policy({"max_name_weight": 0.10})
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1
    assert supervisor.snapshot.last_kill is not None
    assert supervisor.snapshot.last_kill["reason"] == "max_name_weight"


def test_set_policy_keeps_sticky_book_inside_cap_when_broker_mutates(
    tmp_path: Path,
) -> None:
    open_time, _session_close, broker, supervisor = _open_then_idle(
        tmp_path, allocation=0.05
    )
    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()
    assert supervisor.live_book_source() == "heartbeat"
    assert broker.positions.get("AAPL") == pytest.approx(5.0)
    broker.positions = {"AAPL": 15.0}
    supervisor.set_policy({"max_name_weight": 0.10})
    assert supervisor.state != SupervisorState.STOPPED
    assert broker.close_all_count == 0


def test_set_policy_after_heartbeat_does_not_refetch_live_book(tmp_path: Path) -> None:
    open_time, _session_close, broker, supervisor = _open_then_idle(tmp_path)
    broker.advance_now(open_time + timedelta(minutes=10))
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
    supervisor.set_policy({"min_delta_dollar": 5.0})
    assert accounts["n"] == after_tick_accounts
    assert positions["n"] == after_tick_positions
    assert supervisor.state != SupervisorState.STOPPED


def test_start_sleeve_flattens_sticky_book_not_mutated_broker(tmp_path: Path) -> None:
    open_time, _session_close, broker, supervisor = _open_then_idle(tmp_path)
    home = AlphaStrategyHome(root=tmp_path)
    (home.bundle_dir("asb_test") / "risk-envelope.yaml").write_text(
        "max_name_weight: 0.20\n", encoding="utf-8"
    )
    home.runtime_path().write_text(
        yaml.safe_dump({"sleeve_overlays": {"asb_test": {"max_name_weight": 0.10}}}),
        encoding="utf-8",
    )
    supervisor.stop_sleeve("asb_test")
    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()
    assert supervisor.live_book_source() == "heartbeat"
    broker.positions = {"AAPL": 5.0}
    held = supervisor.start_sleeve("asb_test", 0.25)
    assert held is False
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1
    assert supervisor.snapshot.last_kill is not None
    assert supervisor.snapshot.last_kill["reason"] == "max_name_weight"


def test_rebalance_live_flatten_uses_this_fetch_not_sticky_book(tmp_path: Path) -> None:
    open_time, session_close, broker, supervisor = _open_then_idle(
        tmp_path, allocation=0.05
    )
    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()
    assert supervisor.live_book_source() == "heartbeat"
    assert broker.positions.get("AAPL") == pytest.approx(5.0)
    broker.positions = {"AAPL": 15.0}
    supervisor.set_policy({"max_name_weight": 0.10})
    assert supervisor.state != SupervisorState.STOPPED
    broker.advance_now(session_close - timedelta(minutes=10))
    supervisor.tick()
    assert broker.close_all_count == 1
    assert supervisor.state == SupervisorState.STOPPED
    assert supervisor.snapshot.last_kill is not None
    assert supervisor.snapshot.last_kill["reason"] == "max_name_weight"


def test_start_sleeve_while_halted_flattens_when_overlay_breaches_live_book(
    tmp_path: Path,
) -> None:
    broker = FakeBroker(equity=10_000.0, is_open=True)
    broker.positions = {"AAPL": 15.0}
    supervisor = _make_supervisor(tmp_path, broker)
    home = AlphaStrategyHome(root=tmp_path)
    (home.bundle_dir("asb_test") / "risk-envelope.yaml").write_text(
        "max_name_weight: 0.20\n", encoding="utf-8"
    )
    home.runtime_path().write_text(
        yaml.safe_dump({"sleeve_overlays": {"asb_test": {"max_name_weight": 0.05}}}),
        encoding="utf-8",
    )
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor._halt("stale bars")
    assert supervisor.state == SupervisorState.HALTED
    held = supervisor.start_sleeve("asb_test", 0.25)
    assert held is False
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1
    assert supervisor.snapshot.last_kill is not None
    assert supervisor.snapshot.last_kill["reason"] == "max_name_weight"
```

Note: `test_rebalance_live_flatten_uses_this_fetch_not_sticky_book` first tightens to 10% against sticky 5 AAPL (0.05) so account policy is 10% without flattening; then close rebalance sees 15 AAPL (0.15) on **this** fetch and flattens. Combined target is still 0.05 (allocation), so `check_book(combined)` does not fire — only the live-cap check does.

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases \
  tests/alphastrategy/test_halt_flatten.py::test_set_policy_flattens_sticky_book_not_mutated_broker \
  tests/alphastrategy/test_halt_flatten.py::test_set_policy_keeps_sticky_book_inside_cap_when_broker_mutates \
  tests/alphastrategy/test_halt_flatten.py::test_set_policy_after_heartbeat_does_not_refetch_live_book \
  tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_flattens_sticky_book_not_mutated_broker \
  tests/alphastrategy/test_halt_flatten.py::test_rebalance_live_flatten_uses_this_fetch_not_sticky_book \
  tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_while_halted_flattens_when_overlay_breaches_live_book \
  -q
```

Expected: help phrase missing; sticky flatten tests fail because `_enforce_live_book` still fetches the mutated broker. The halted+overlay lock may already pass — keep it.

- [ ] **Step 3: Commit failing tests and docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-book-enforce-requirements.md \
  docs/plans/2026-08-20-alphastrategy-book-enforce-technical-design.md \
  tests/alphastrategy/test_helptext.py tests/alphastrategy/test_halt_flatten.py
git commit -m "test: flatten-now uses the same live book as Book"
```

---

### Task 2: Engine + help

**Files:**
- Modify: `src/alphastrategy/supervisor/loop.py`
- Modify: `src/alphastrategy/helptext.py`
- Modify: `README.md`

- [ ] **Step 1: Unlocked live book + enforce signature**

Replace `live_book` / `_live_book_weights` / `_enforce_live_book` with:

```python
    def _live_book_unlocked(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
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

    def live_book(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        with self._lock:
            return self._live_book_unlocked()

    def _live_book_weights(
        self, equity: float, raw_positions: list[dict[str, Any]]
    ) -> dict[str, float]:
        positions = _positions_map(raw_positions)
        prices = dict(self._snapshot.last_prices)
        if equity > 0 and prices:
            got = {
                symbol: (qty * prices[symbol]) / equity
                for symbol, qty in positions.items()
                if symbol in prices
            }
            if got:
                return got
        if self._snapshot.last_got:
            return dict(self._snapshot.last_got)
        return dict(self._snapshot.last_combined)

    def _enforce_live_book(
        self,
        account: dict[str, Any] | None = None,
        positions: list[dict[str, Any]] | None = None,
    ) -> None:
        if self._broker is None:
            return
        if self._snapshot.state in (
            SupervisorState.FLATTENING,
            SupervisorState.STOPPED,
        ):
            return
        try:
            if account is None or positions is None:
                account, positions = self._live_book_unlocked()
            equity = float(account.get("equity", 0))
            weights = self._live_book_weights(equity, positions)
        except Exception as exc:
            self._halt(f"tighten live book: {exc}")
            return
        try:
            check_book(weights, equity, self._rebalance_policy())
        except FlattenRequested as exc:
            reason = exc.reason or "limit"
            self._flatten_account(reason=reason)
            self._record_kill(
                KillOutcome(
                    isolated=False,
                    flattened=True,
                    scope="account",
                    reason=reason,
                    bundle_id=None,
                )
            )
```

In `_rebalance`, fetch account once and pass the pair:

```python
        account = self._broker.get_account()
        equity = float(account.get("equity", 0))
        rebalance_policy = self._rebalance_policy()
        check_book(combined, equity, rebalance_policy)

        raw_positions = self._broker.list_positions()
        positions = _positions_map(raw_positions)
        symbols = set(combined) | set(positions)
        prices = self._fetch_prices(symbols, now=cur.now if cur.is_open else None)
        # ... last_sleeve_weights / contribution / last_combined / last_prices unchanged ...
        self._enforce_live_book(account, raw_positions)
```

Keep `_equity()` for other callers. Do not call `live_book()` from `_place_batch`.

- [ ] **Step 2: Help and README**

Insert `Tighten and Start paper flatten the same live book as Book. ` immediately after `A heartbeat live book holds until flatten or place. ` in `execution`, and after `Tighten that breaches the live book flattens now. ` in `halt_flatten`, `how_risk`, and `task_tighten`. Add the same sentence to `task_start` after the overlay-start sentence. README Operator, after the sticky-book sentence:

```text
  Tighten and Start paper flatten the same live book as Book.
```

- [ ] **Step 3: Run the new tests**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases \
  tests/alphastrategy/test_halt_flatten.py::test_set_policy_flattens_sticky_book_not_mutated_broker \
  tests/alphastrategy/test_halt_flatten.py::test_set_policy_keeps_sticky_book_inside_cap_when_broker_mutates \
  tests/alphastrategy/test_halt_flatten.py::test_set_policy_after_heartbeat_does_not_refetch_live_book \
  tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_flattens_sticky_book_not_mutated_broker \
  tests/alphastrategy/test_halt_flatten.py::test_rebalance_live_flatten_uses_this_fetch_not_sticky_book \
  tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_while_halted_flattens_when_overlay_breaches_live_book \
  tests/alphastrategy/test_halt_flatten.py::test_set_policy_flattens_when_live_book_breaches_gross \
  tests/alphastrategy/test_halt_flatten.py::test_start_sleeve_flattens_when_idle_overlay_breaches_live_book \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_live_book_holds_past_ttl \
  tests/alphastrategy/test_halt_flatten.py::test_close_rebalance_flattens_live_book_after_price_rally \
  -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/alphastrategy/supervisor/loop.py src/alphastrategy/helptext.py README.md
git commit -m "feat: flatten-now uses the same live book as Book"
```

---

### Task 3: Full suite

- [ ] **Step 1: Run**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q
```

Expected: all passed.

- [ ] **Step 2: Commit any fixes, push, update PR**

## Spec coverage

| Requirement | Task |
| --- | --- |
| Operator flatten-now uses desk live book | 1–2 |
| Sticky vs mutated broker (flatten / no flatten) | 1 |
| No extra fetch after heartbeat on min_delta tighten | 1 |
| start_sleeve uses sticky book | 1 |
| Rebalance uses this fetch | 1–2 |
| Halted + overlay start flatten wins | 1 (lock) |
| Help phrase | 1–2 |
| Orders still not glance-fed | 2 (`_rebalance` own fetch) |

No placeholders. `_equity()` remains for any leftover caller; rebalance stops using it for the live-cap path.
