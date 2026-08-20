# Heartbeat Live-Book Seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Heartbeat seeds `live_book()` with the same account/positions it used for `last_got`; sleeve envelopes parse once per file digest.

**Architecture:** `_heartbeat_health_check` fetches once and writes `_live_book_cache`. `_bundle_envelope` digest-caches parsed dicts (SHA-256 of bytes, not mtime+size). Order paths still hit the broker.

**Tech Stack:** Supervisor, pytest, helptext, README.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-beat-book-requirements.md`](../requirements/2026-08-20-alphastrategy-beat-book-requirements.md)

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
    "Heartbeat seeds the live book glance",
    "Sleeve envelopes load once until the file changes",
```

In `tests/alphastrategy/test_api.py` after `test_status_portfolio_risk_share_one_live_book`:

```python
def test_tick_seeds_live_book_for_status_and_portfolio(api_stack) -> None:
    client, _home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 4.0}
    supervisor.tick()
    accounts = broker.account_reads
    positions = broker.position_reads
    client.get("/api/status")
    client.get("/api/portfolio")
    assert broker.account_reads == accounts
    assert broker.position_reads == positions
```

In `tests/alphastrategy/test_halt_flatten.py` after `test_sleeve_policies_read_runtime_once`:

```python
def test_heartbeat_seeds_live_book_without_extra_broker_reads(tmp_path: Path) -> None:
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
    supervisor.live_book()
    assert accounts["n"] == after_tick_accounts
    assert positions["n"] == after_tick_positions
    assert after_tick_accounts >= 1
    assert after_tick_positions >= 1


def test_bundle_envelope_parses_once_while_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alphastrategy.bundle.schema import load_risk_envelope

    loads = {"n": 0}
    orig = load_risk_envelope

    def counted(data: bytes) -> dict:
        loads["n"] += 1
        return orig(data)

    monkeypatch.setattr(
        "alphastrategy.supervisor.loop.load_risk_envelope", counted
    )
    home = AlphaStrategyHome(root=tmp_path)
    supervisor = _make_supervisor(
        tmp_path,
        FakeBroker(),
        evaluators={"asb_a": {"AAPL": 1.0}, "asb_b": {"MSFT": 1.0}},
    )
    (home.bundle_dir("asb_a") / "risk-envelope.yaml").write_text(
        "max_name_weight: 0.20\n", encoding="utf-8"
    )
    (home.bundle_dir("asb_b") / "risk-envelope.yaml").write_text(
        "max_name_weight: 0.20\n", encoding="utf-8"
    )
    supervisor.start_sleeve("asb_a", 0.1)
    supervisor.start_sleeve("asb_b", 0.1)
    after_start = loads["n"]
    supervisor.sleeve_policies(["asb_a", "asb_b"])
    supervisor.sleeve_policies(["asb_a", "asb_b"])
    supervisor.spoken_policy()
    assert loads["n"] == after_start


def test_spoken_policy_sees_envelope_yaml_write(tmp_path: Path) -> None:
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    home = AlphaStrategyHome(root=tmp_path)
    envelope = home.bundle_dir("asb_test") / "risk-envelope.yaml"
    envelope.write_text("max_name_weight: 0.10\n", encoding="utf-8")
    supervisor.start_sleeve("asb_test", 0.25)
    assert supervisor.spoken_policy().max_name_weight == pytest.approx(0.10)
    envelope.write_text("max_name_weight: 0.05\n", encoding="utf-8")
    assert supervisor.spoken_policy().max_name_weight == pytest.approx(0.05)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_api.py::test_tick_seeds_live_book_for_status_and_portfolio \
  tests/alphastrategy/test_halt_flatten.py::test_heartbeat_seeds_live_book_without_extra_broker_reads \
  tests/alphastrategy/test_halt_flatten.py::test_bundle_envelope_parses_once_while_unchanged \
  tests/alphastrategy/test_halt_flatten.py::test_spoken_policy_sees_envelope_yaml_write \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL. Tick then GET/live_book extra broker reads. Envelope parsed again. Help phrases missing.

If `test_spoken_policy_sees_envelope_yaml_write` PASSES on RED (spoken cache key already includes envelope stamp), keep it as a lock.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git commit -m "test: heartbeat seeds live book; envelope stamp cache"
```

---

### Task 2: Engine + help

- [ ] **Step 1: Heartbeat seed**

Rewrite `_heartbeat_health_check` to fetch `raw_positions` then `account`, seed `_live_book_cache`, then existing mark logic using `float(account.get("equity", 0))` instead of `_equity()`. Empty universe returns **after** the seed.

- [ ] **Step 2: Envelope digest cache**

mtime+size is not enough: `test_spoken_policy_sees_envelope_yaml_write` rewrites `0.10` → `0.05` at the same byte length. Spoken keys and `_bundle_envelope` must use SHA-256 of the file bytes.

In `__init__`: `self._envelope_cache: dict[str, tuple[str, dict[str, Any]]] = {}`

```python
    def _file_digest(self, path: Path) -> str:
        if not path.is_file():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _bundle_envelope(self, bundle_id: str) -> dict[str, Any]:
        envelope_path = self._home.bundle_dir(bundle_id) / "risk-envelope.yaml"
        if not envelope_path.is_file():
            raw = b""
            digest = ""
        else:
            raw = envelope_path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
        cached = self._envelope_cache.get(bundle_id)
        if cached is not None and cached[0] == digest:
            return cached[1]
        doc: dict[str, Any] = load_risk_envelope(raw) if raw else {}
        self._envelope_cache[bundle_id] = (digest, doc)
        return doc
```

`_spoken_cache_key` envelope tuple uses `_file_digest(...)`, not `_file_stamp`.

- [ ] **Step 3: Help / README**

Execution section after heartbeat marks: `Heartbeat seeds the live book glance.`

`how_risk` after overlays load runtime: `Sleeve envelopes load once until the file changes.`

README heartbeat bullet: both sentences.

- [ ] **Step 4: Targeted tests then full suite**

Keep `test_heartbeat_refreshes_last_prices_without_flattening`.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: heartbeat seeds live book; envelope stamp cache"
```
