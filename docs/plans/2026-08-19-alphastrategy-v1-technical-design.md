# alphastrategy v1 Technical Design and Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace this repo’s product identity with a local Alpaca-paper execution desk that imports alphaloop `.asb` bundles, evaluates a closed DSL in a sandbox, and places paper orders through a single Supervisor.

**Architecture:** New package `src/alphastrategy/` (do not grow `src/openstrategy/` as the product). A localhost control plane and CLI talk to one Supervisor process that owns Alpaca keys and is the only order placer. Each running bundle is a sleeve subprocess that returns target weights over stdin/stdout JSON. Combined book is `Σ allocation_i * weight_i`. Halt vs flatten follows the requirements matrix. Quiet cockpit static Web is served from the same process.

**Tech Stack:** Python 3.9+, pandas, numpy, PyYAML, stdlib (`zipfile`, `hashlib`, `json`, `subprocess`, `http.server`, `urllib.request`). No Node at runtime. Web is hand-authored HTML/CSS/JS using the Quiet cockpit tokens. Tests use pytest and mock HTTP; they never call a real broker.

**Requirements:** [`docs/requirements/2026-08-19-alphastrategy-v1-requirements.md`](../requirements/2026-08-19-alphastrategy-v1-requirements.md)

## Global Constraints

- Package name `alphastrategy`, CLI `alphastrategy`, version line `0.1.0` (not openstrategy 1.1.4).
- Tag `v1.1.3` (`41cbdff78d12080f82d1e61790df33e92ea29540`) stays the honest-tool snapshot.
- v1 venue is Alpaca paper only: `https://paper-api.alpaca.markets`.
- Live construction still requires `paper=False` and `confirm_live=True` (`confirm_yes_i_know_what_im_doing`); v1 CLI and Web must not expose a live control.
- No broker credentials in `.asb`, logs, or the Web UI.
- Strategy logic never sees secrets, network, or the broker object.
- Import is not permission to trade; paper start is a second explicit human action.
- No telemetry back to alphaloop; no auto-promote.
- Market profile v1: only `us-equity-daily`.
- Supported version pair: `schema_version=alphastrategy.bundle/v0` and `dsl_version=alphaloop.dsl/v0` only.
- Content hash: SHA-256 of uncompressed zip members in sorted path order, excluding `bundle.yaml`. `bundle_id` = `asb_` + first 16 hex chars.
- Conformance tolerance: abs `1e-9` or rel `1e-6` (larger wins); extra or missing assets fail.
- Heartbeat 20s (no orders). Open rebalance: 3 minutes after `is_open` false→true. Close rebalance: 12 minutes before `next_close`.
- RTH paper **market** orders only.
- Sandbox: 5s wall clock, 512MB memory, no env secrets, no network.
- Account defaults: long-only; gross ≤ 100% equity; single-name ≤ 20%; ≤ 50 names; single order ≤ 20% equity; ≤ 100 orders/rebalance; ≤ 200 orders/day; min delta `max($1, 0.1% equity)`.
- Control plane binds localhost only.
- Tests never place a real order.

---

## A. Technical design

### A.1 Package layout

Create these files. Do not add execution features under `src/openstrategy/`. Keep that tree until Phase 4 unships it.

```text
src/alphastrategy/
  __init__.py                 # __version__ = "0.1.0"
  __main__.py                 # python -m alphastrategy
  home.py                     # AlphaStrategyHome paths
  errors.py                   # ImportRejected, LiveTradingRefused re-export, HaltError
  bundle/
    __init__.py
    hash.py                   # content_hash, bundle_id_from_hash
    archive.py                # load/save .asb zip, member whitelist
    schema.py                 # dataclasses + YAML load, support table
    import_bundle.py          # import_asb(path, home) -> ImportedBundle
  dsl/
    __init__.py
    grammar.py                # parse strategy.dsl.yaml, unknown op fails
    factors.py                # vendored 10 factor functions (copy math from openstrategy.engineer)
    eval.py                   # evaluate(dsl, bars, params) -> dict[str, float]
    worker.py                 # subprocess entry: read JSON stdin, write JSON stdout
    sandbox.py                # run_interpreter(bundle_dir, bars, effective_at) -> weights
  live/
    __init__.py
    broker.py                 # copy hard wall from openstrategy.live.broker + new methods
    alpaca.py                 # paper adapter + positions/orders/bars/clock
  risk/
    __init__.py
    policy.py                 # AccountPolicy defaults, merge with envelope, tighten-only
    check.py                  # limit breach -> FlattenDecision | ok
  supervisor/
    __init__.py
    state.py                  # SupervisorState enum + persisted JSON
    combine.py                # combined[asset] = Σ allocation_i * weight_i
    clock.py                  # RebalanceEvent from Alpaca clock
    orders.py                 # weights -> market orders, execution_deviation
    audit.py                  # append-only JSONL, redaction
    loop.py                   # Supervisor: heartbeat, rebalance, halt, flatten
  api/
    __init__.py
    app.py                    # stdlib HTTP server, JSON + static
    handlers.py               # import/start/stop/kill/resume/status
  cli/
    __init__.py
    main.py                   # alphastrategy entry
  web/
    static/index.html
    static/styles.css         # Quiet cockpit tokens
    static/app.js             # five screens
tests/alphastrategy/
  conftest.py
  fixtures/golden.asb         # built in test setup or checked-in zip
  fixtures/golden/            # unpacked members used to build the zip
  test_bundle_hash.py
  test_bundle_import.py
  test_dsl_eval.py
  test_sandbox.py
  test_combine.py
  test_clock.py
  test_risk.py
  test_orders.py
  test_halt_flatten.py
  test_audit.py
  test_alpaca_paper.py
  test_safety.py
  test_cli.py
  test_api.py
  test_web_tokens.py
  test_e2e_mocked.py
```

On-disk home (default `~/.alphastrategy`, override `ALPHASTRATEGY_HOME`):

```text
imported/<bundle_id>/         # unpacked members + import-meta.json
runtime.yaml                  # account policy + allocations
supervisor-state.json
audit.jsonl
```

### A.2 Errors

```python
class ImportRejected(ValueError):
    """Fail-closed import. str(e) is shown in CLI and Web."""

class IllegalWeights(ValueError):
    """DSL output failed long-only / finite / sum-to-1 checks."""

class HaltRequested(Exception):
    """Health halt: no new orders, do not flatten."""

class FlattenRequested(Exception):
    def __init__(self, scope: str):
        # scope is "account" or f"sleeve:{bundle_id}"
        self.scope = scope
```

`LiveTradingRefused` stays in `alphastrategy.live.broker` with the same message and `CONFIRM_LIVE_FLAG = "confirm_yes_i_know_what_im_doing"`.

### A.3 Bundle member whitelist and hash

Allowed members (files or prefix):

- `bundle.yaml`
- `strategy.dsl.yaml`
- `market-profile.yaml`
- `parameters.yaml`
- `risk-envelope.yaml`
- `lineage.yaml`
- `evidence/` (any file under this prefix)
- `conformance/` (any file under this prefix)

Reject: `..`, absolute paths, `.py`, `.so`, `.dll`, `.exe`, members outside the whitelist.

```python
def content_hash(members: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in members if p != "bundle.yaml"):
        h.update(path.encode("utf-8") + b"\0")
        h.update(members[path] + b"\0")
    return h.hexdigest()

def bundle_id_from_hash(sha256_hex: str) -> str:
    return "asb_" + sha256_hex[:16]
```

### A.4 YAML schemas (v0)

`bundle.yaml`:

```yaml
schema_version: alphastrategy.bundle/v0
dsl_version: alphaloop.dsl/v0
bundle_id: asb_0123456789abcdef
content_hash: "<64 hex>"
created_at: "2026-08-19T00:00:00Z"
registry_uri: null
```

Reject if any key looks like `api_key`, `secret`, `password`, `token`, `credential`.

`market-profile.yaml`:

```yaml
id: us-equity-daily
calendar: NYSE
benchmark: SPY
```

`lineage.yaml`:

```yaml
run_id: "run_example"
candidate_id: "cand_example"
research_outcome: FOUND
engine_hash: "deadbeef"
data_snapshot_hash: "cafebabe"
```

`evidence/summary.yaml` (required file):

```yaml
passes_all: true
gates: [dsr, cv, consistency, vs_random, vs_buyhold, vs_spy]
```

`risk-envelope.yaml` (missing field → account default, never unlimited):

```yaml
long_only: true
max_gross: 1.0
max_name_weight: 0.20
max_names: 50
max_order_notional_frac: 0.20
max_orders_per_rebalance: 100
max_orders_per_day: 200
```

`parameters.yaml`: JSON-compatible mapping only.

`strategy.dsl.yaml`:

```yaml
dsl_version: alphaloop.dsl/v0
universe: [AAPL, MSFT]
steps:
  - op: equal_weight
  - op: clip
    params:
      max: 0.55
  - op: cash
    params:
      min_cash: 0.0
```

Closed `op` set: `rsi`, `macd`, `roc`, `momentum_12_1`, `bollinger_zscore`, `ohlr_4_pct`, `pairs_spread`, `atr_breakout`, `parkinson_hist_vol`, `obv_slope`, `normalize`, `clip`, `equal_weight`, `cash`.

`conformance/bars.csv`: DatetimeIndex in column `date`, one close column per universe symbol.

`conformance/expected_weights.yaml`:

```yaml
effective_at: "2024-01-31"
weights:
  AAPL: 0.5
  MSFT: 0.5
```

### A.5 DSL evaluation

Input bars: `pandas.DataFrame` indexed by `DatetimeIndex`, columns = symbols, values = close.

Pipeline:

1. Start from zeros per symbol.
2. Factor ops (`rsi` … `obv_slope`) compute a `[0,1]` series per column using vendored functions (copy from `src/openstrategy/engineer/`, do not import `openstrategy` at runtime). Take the last row at `effective_at` (or last index ≤ `effective_at`).
3. `equal_weight` sets each universe symbol to `1/n`.
4. `normalize` rescales finite non-negative weights to sum 1 (if sum is 0, all cash).
5. `clip` applies `params.max` (default 0.2) per name then renormalize if needed.
6. `cash` ensures `sum(weights) <= 1 - min_cash`.

Illegal if any weight `< 0`, non-finite, symbol not in universe, or `sum > 1 + 1e-9`.

`pairs_spread` requires `params.leg_a` and `params.leg_b` in universe; other symbols stay 0 before normalize.

### A.6 Sandbox IPC

Parent writes one JSON object to worker stdin and closes stdin:

```json
{
  "bundle_dir": "/abs/path/imported/asb_…",
  "effective_at": "2024-01-31T20:00:00Z",
  "bars": {"date": ["2024-01-30", "2024-01-31"], "AAPL": [100.0, 101.0], "MSFT": [200.0, 201.0]}
}
```

Worker stdout (success):

```json
{"ok": true, "weights": {"AAPL": 0.5, "MSFT": 0.5}}
```

Worker stdout (failure): `{"ok": false, "error": "unknown op: foo"}` and exit 2.

Parent:

```python
env = {
    "PATH": os.environ.get("PATH", ""),
    "PYTHONPATH": str(src_root),
    "HOME": str(tmp_home),
    "LANG": "C",
}
subprocess.run(
    [sys.executable, "-m", "alphastrategy.dsl.worker"],
    cwd=str(bundle_dir),
    env=env,
    input=payload,
    capture_output=True,
    timeout=5,
    check=False,
)
```

Do not pass `ALPACA_*` or other secrets. Apply `resource.RLIMIT_AS` of 512MB in `worker.py` at startup when `resource` is available; if the platform cannot set it, tests skip only the memory-cap case, never the timeout case.

Any worker exception, timeout, non-zero exit, or illegal weights → `HaltRequested` at Supervisor (do not flatten).

### A.7 Combine, orders, halt, flatten

```python
def combine(sleeves: list[tuple[float, dict[str, float]]]) -> dict[str, float]:
    # allocations must be >= 0 and sum <= 1.0
    out: dict[str, float] = {}
    for alloc, weights in sleeves:
        for asset, w in weights.items():
            out[asset] = out.get(asset, 0.0) + alloc * w
    return out
```

Residual `1 - sum(combined)` is cash (not an asset order).

Order mapping (paper market):

- `target_qty = floor((combined[asset] * equity) / last_price)` using whole shares.
- `delta = target_qty - position_qty`.
- Skip if `abs(delta) * last_price < max(1.0, 0.001 * equity)`.
- Place market `buy`/`sell` on paper.
- After fills (or mocked fills), if remaining notional gap still exceeds min delta, append audit event `execution_deviation` with `{asset, wanted, got}`. Do not change DSL.

Clock:

```python
@dataclass(frozen=True)
class ClockSnapshot:
    is_open: bool
    next_open: datetime
    next_close: datetime
    now: datetime

def next_rebalance_event(prev: ClockSnapshot | None, cur: ClockSnapshot, last_event: str | None) -> str | None:
    # returns "open", "close", or None
```

- `"open"` once when `prev.is_open is False` and `cur.is_open is True` and `now >= prev.next_open + 3 minutes` (if `prev` is None, use `cur.next_open`). Persist `last_rebalance_event = f"{session_date}:open"`.
- `"close"` once when `cur.is_open` and `cur.next_close - now <= 12 minutes` and last event is not `f"{session_date}:close"`.

Health halt when: broker call raises, last bar older than 2 trading days at RTH, `is_open` True outside 13:30–21:00 UTC weekday window (unexpected session), illegal weights, sandbox death.

Flatten account: `cancel` open orders then `close_all`. Sleeve kill: recompute combined without that sleeve; if the implied sells cannot be attributed (missing last prices), flatten account instead.

### A.8 Broker protocol additions

Copy `openstrategy.live.broker` and `alpaca.py` into `alphastrategy.live`. Keep `_enforce_safety`. Extend `Broker`:

```python
def list_positions(self) -> list[dict]: ...
def place_order(self, symbol: str, qty: float, side: str) -> dict: ...
def cancel_order(self, order_id: str) -> None: ...
def close_all(self) -> None: ...
def get_clock(self) -> dict: ...
def get_bars(self, symbols: list[str], start: str, end: str) -> dict: ...
```

`AlpacaAdapter.place_order` POSTs `/v2/orders` with `{"symbol", "qty", "side", "type": "market", "time_in_force": "day"}`. v1 Supervisor constructs `AlpacaAdapter(paper=True, ...)` only. CLI/API reject `--live`, `paper=false`, and `confirm_live`.

Bars: GET Alpaca market-data v2 daily bars (`/v2/stocks/{symbol}/bars`). Tests mock this; never hit the network.

### A.9 HTTP API (localhost)

`alphastrategy start --host 127.0.0.1 --port 7460` serves `web/static` and:

| Method | Path | Body | Result |
| --- | --- | --- | --- |
| GET | `/api/status` | | state, clock, halt flag |
| GET | `/api/portfolio` | | equity, cash, pnl, positions, sleeves |
| GET | `/api/bundles` | | imported + paper list |
| POST | `/api/import` | multipart file | import or 400 `{error}` |
| POST | `/api/paper/start` | `{bundle_id, allocation}` | 409 if sum>1 |
| POST | `/api/paper/stop` | `{bundle_id}` | stop = zero at next rebalance |
| POST | `/api/paper/kill` | `{bundle_id?}` | flatten sleeve or account |
| POST | `/api/paper/resume` | | clear halt, no catch-up order |
| GET | `/api/activity` | | last audit events |
| GET | `/api/risk` | | account + per-sleeve |
| PUT | `/api/risk` | tighten-only patch | 400 if looser than envelope |

No route sets `paper=False`. No live toggle in HTML.

### A.10 Quiet cockpit Web

Tokens (requirements §8): background `#0b0e14`, surface `#11151d`, border `#2a3142`, text `#e5e9f0`, muted `#5c6573` / `#9ba3b4`, running `#10b981`, halt `#f59e0b`, fail `#ef4444`. system-ui, tabular-nums.

Single-page `index.html` with nav: Portfolio, Strategies, Run, Activity, Risk. Halt/deviation banners on Portfolio use halt/fail colors and remain visible while the condition holds.

### A.11 Identity cut (Phase 4)

- `pyproject.toml`: `name = "alphastrategy"`, `version = "0.1.0"`, script `alphastrategy = "alphastrategy.cli.main:main"`, hatch packages `src/alphastrategy`.
- README rewritten as paper desk; link alphaloop for research; keep historical note about `v1.1.3`.
- Stop shipping `openstrategy` console script. Leave `src/openstrategy/` in git history; remove from wheel (do not package it).
- Drop product entry for Streamlit, `openstrategy report`, Yahoo/AKShare/CCXT/OpenBB extras.
- Old `tests/` under openstrategy may remain but are not the product gate; product gate is `tests/alphastrategy/`.

### A.12 Audit JSONL

Each line is a JSON object: `{ts, event, ...payload}`. Events: `import`, `paper_start`, `paper_stop`, `rebalance`, `order`, `fill`, `execution_deviation`, `halt`, `flatten`, `resume`, `kill`. Redact keys whose names contain `key`, `secret`, `token`, `password`. Tests assert redaction.

---

## B. Implementation tasks

Implement in order. Each phase must stay green before the next. Commit after every task.

### Task 1: Home paths, errors, package stub

**Files:**
- Create: `src/alphastrategy/__init__.py`
- Create: `src/alphastrategy/home.py`
- Create: `src/alphastrategy/errors.py`
- Test: `tests/alphastrategy/test_home.py`

**Interfaces:**
- Consumes: nothing
- Produces: `AlphaStrategyHome.from_env(env: dict | None = None) -> AlphaStrategyHome` with `.root`, `.imported_dir()`, `.bundle_dir(bundle_id: str)`, `.runtime_path()`, `.audit_path()`, `.state_path()`; `ImportRejected`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from alphastrategy.home import AlphaStrategyHome

def test_home_uses_env_override(tmp_path: Path):
    home = AlphaStrategyHome.from_env({"ALPHASTRATEGY_HOME": str(tmp_path)})
    assert home.root == tmp_path
    assert home.bundle_dir("asb_abc") == tmp_path / "imported" / "asb_abc"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/alphastrategy/test_home.py::test_home_uses_env_override -v`

Expected: FAIL with `ModuleNotFoundError: alphastrategy`

- [ ] **Step 3: Write minimal implementation**

```python
# src/alphastrategy/__init__.py
__version__ = "0.1.0"
```

```python
# src/alphastrategy/errors.py
class ImportRejected(ValueError):
    """Fail-closed import. str(e) is shown in CLI and Web."""


class IllegalWeights(ValueError):
    """DSL output failed long-only / finite / sum-to-1 checks."""


class HaltRequested(Exception):
    """Health halt: no new orders, do not flatten."""


class FlattenRequested(Exception):
    def __init__(self, scope: str):
        super().__init__(scope)
        self.scope = scope
```

```python
# src/alphastrategy/home.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class AlphaStrategyHome:
    root: Path

    @classmethod
    def from_env(cls, env: dict | None = None) -> "AlphaStrategyHome":
        e = os.environ if env is None else env
        raw = e.get("ALPHASTRATEGY_HOME") or str(Path.home() / ".alphastrategy")
        return cls(root=Path(raw))

    def imported_dir(self) -> Path:
        return self.root / "imported"

    def bundle_dir(self, bundle_id: str) -> Path:
        return self.imported_dir() / bundle_id

    def runtime_path(self) -> Path:
        return self.root / "runtime.yaml"

    def audit_path(self) -> Path:
        return self.root / "audit.jsonl"

    def state_path(self) -> Path:
        return self.root / "supervisor-state.json"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/alphastrategy/test_home.py -v`

Expected: PASS. Ensure `pyproject.toml` still has `packages = ["src/openstrategy"]` until Phase 4; run tests with `PYTHONPATH=src`.

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/home.py src/alphastrategy/errors.py src/alphastrategy/__init__.py tests/alphastrategy/test_home.py
git commit -m "feat: add alphastrategy home paths"
```

### Task 2: Content hash and zip whitelist

**Files:**
- Create: `src/alphastrategy/bundle/hash.py`
- Create: `src/alphastrategy/bundle/archive.py`
- Create: `src/alphastrategy/bundle/__init__.py`
- Test: `tests/alphastrategy/test_bundle_hash.py`

**Interfaces:**
- Consumes: `ImportRejected`
- Produces: `content_hash(members: dict[str, bytes]) -> str`; `bundle_id_from_hash(sha256_hex: str) -> str`; `read_asb(path: Path) -> dict[str, bytes]`; `ALLOWED_PREFIXES` / `is_allowed_member(name: str) -> bool`

- [ ] **Step 1: Write the failing test**

```python
import hashlib
from alphastrategy.bundle.hash import content_hash, bundle_id_from_hash
from alphastrategy.bundle.archive import is_allowed_member

def test_hash_excludes_bundle_yaml_and_is_order_stable():
    a = {"bundle.yaml": b"x", "lineage.yaml": b"b", "strategy.dsl.yaml": b"a"}
    b = {"strategy.dsl.yaml": b"a", "lineage.yaml": b"b", "bundle.yaml": b"CHANGED"}
    assert content_hash(a) == content_hash(b)
    assert len(content_hash(a)) == 64
    assert bundle_id_from_hash(content_hash(a)).startswith("asb_")

def test_rejects_python_member():
    assert is_allowed_member("strategy.dsl.yaml") is True
    assert is_allowed_member("evil.py") is False
    assert is_allowed_member("../x") is False
    assert is_allowed_member("evidence/summary.yaml") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_bundle_hash.py -v`

Expected: FAIL import error or assertion

- [ ] **Step 3: Write minimal implementation**

```python
import hashlib
from pathlib import Path
import zipfile
from alphastrategy.errors import ImportRejected

def content_hash(members: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in members if p != "bundle.yaml"):
        h.update(path.encode("utf-8") + b"\0")
        h.update(members[path] + b"\0")
    return h.hexdigest()

def bundle_id_from_hash(sha256_hex: str) -> str:
    return "asb_" + sha256_hex[:16]

_ALLOWED = {
    "bundle.yaml", "strategy.dsl.yaml", "market-profile.yaml",
    "parameters.yaml", "risk-envelope.yaml", "lineage.yaml",
}

def is_allowed_member(name: str) -> bool:
    if ".." in name or name.startswith("/") or "\\" in name:
        return False
    lower = name.lower()
    if lower.endswith((".py", ".so", ".dll", ".exe")):
        return False
    if name in _ALLOWED:
        return True
    return name.startswith("evidence/") or name.startswith("conformance/")

def read_asb(path: Path) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if not is_allowed_member(name):
                raise ImportRejected(f"illegal member: {name}")
            members[name] = zf.read(name)
    return members
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_bundle_hash.py -v`

- [ ] **Step 5: Commit** `feat: hash and whitelist .asb archives`

### Task 3: Schema load and fail-closed import (without DSL eval)

**Files:**
- Create: `src/alphastrategy/bundle/schema.py`
- Create: `src/alphastrategy/bundle/import_bundle.py`
- Test: `tests/alphastrategy/test_bundle_import.py`
- Create: `tests/alphastrategy/fixtures/make_asb.py` helper used by tests

**Interfaces:**
- Consumes: `read_asb`, `content_hash`, `bundle_id_from_hash`, `AlphaStrategyHome`
- Produces: `import_asb(path: Path, home: AlphaStrategyHome) -> str` (bundle_id); raises `ImportRejected`

- [ ] **Step 1: Failing tests** — hash mismatch; `research_outcome != FOUND`; `passes_all: false`; `market-profile.id != us-equity-daily`; unsupported `schema_version`; secret-like key in `bundle.yaml`.

```python
import io
import zipfile
from pathlib import Path
from alphastrategy.errors import ImportRejected
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.bundle.import_bundle import import_asb
from tests.alphastrategy.fixtures.make_asb import build_golden_asb, mutate_member

def test_import_rejects_hash_mismatch(tmp_path: Path):
    raw = build_golden_asb()
    broken = mutate_member(raw, "strategy.dsl.yaml", b"steps: []\n")
    dest = tmp_path / "bad.asb"
    dest.write_bytes(broken)
    home = AlphaStrategyHome.from_env({"ALPHASTRATEGY_HOME": str(tmp_path / "home")})
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected as e:
        assert "hash" in str(e).lower()

def test_import_rejects_not_found_outcome(tmp_path: Path):
    raw = mutate_member(build_golden_asb(), "lineage.yaml", b"research_outcome: NO_EVIDENCE\n")
    dest = tmp_path / "nofound.asb"
    dest.write_bytes(raw)
    home = AlphaStrategyHome.from_env({"ALPHASTRATEGY_HOME": str(tmp_path / "home")})
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected as e:
        assert "FOUND" in str(e)
```

`tests/alphastrategy/fixtures/make_asb.py` builds a zip from `tests/alphastrategy/fixtures/golden/` (write those YAML files in this task). For this task, `import_asb` may skip sandbox eval but must still require `conformance/` members to exist.

- [ ] **Step 2: Run tests — expect FAIL**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_bundle_import.py -v`

- [ ] **Step 3: Implement YAML dataclasses and checks**

`tests/alphastrategy/fixtures/make_asb.py`:

```python
import io
import zipfile
from pathlib import Path
from alphastrategy.bundle.hash import content_hash, bundle_id_from_hash

FIXTURE_DIR = Path(__file__).parent / "golden"

def _members_from_dir() -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    for p in FIXTURE_DIR.rglob("*"):
        if p.is_file():
            rel = p.relative_to(FIXTURE_DIR).as_posix()
            members[rel] = p.read_bytes()
    return members

def build_golden_asb() -> bytes:
    members = _members_from_dir()
    sha = content_hash(members)
    bid = bundle_id_from_hash(sha)
    members["bundle.yaml"] = (
        "schema_version: alphastrategy.bundle/v0\n"
        "dsl_version: alphaloop.dsl/v0\n"
        f"bundle_id: {bid}\n"
        f"content_hash: {sha}\n"
        "created_at: '2026-08-19T00:00:00Z'\n"
        "registry_uri: null\n"
    ).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in sorted(members.items()):
            zf.writestr(name, data)
    return buf.getvalue()

def mutate_member(asb_bytes: bytes, name: str, new: bytes) -> bytes:
    buf_in = io.BytesIO(asb_bytes)
    out = io.BytesIO()
    with zipfile.ZipFile(buf_in) as zin, zipfile.ZipFile(out, "w") as zout:
        for item in zin.infolist():
            data = new if item.filename == name else zin.read(item.filename)
            zout.writestr(item.filename, data)
    return out.getvalue()
```

Support table:

```python
SUPPORTED = {("alphastrategy.bundle/v0", "alphaloop.dsl/v0")}
```

Write unpacked tree to `home.bundle_dir(bundle_id)` only after all checks except sandbox eval pass. Write `import-meta.json` with `{imported_at, source_path}`.

- [ ] **Step 4: Tests PASS**

- [ ] **Step 5: Commit** `feat: fail-closed .asb import checks`

### Task 4: In-process DSL evaluator

**Files:**
- Create: `src/alphastrategy/dsl/grammar.py`
- Create: `src/alphastrategy/dsl/factors.py` (copy functions from `src/openstrategy/engineer/*.py`, drop `@no_lookahead` decorator to keep eval fast)
- Create: `src/alphastrategy/dsl/eval.py`
- Test: `tests/alphastrategy/test_dsl_eval.py`

**Interfaces:**
- Consumes: parsed `strategy.dsl.yaml` + `parameters.yaml`
- Produces: `evaluate_dsl(dsl: dict, bars: pandas.DataFrame, effective_at, params: dict) -> dict[str, float]`; `IllegalWeights`

- [ ] **Step 1: Failing tests**

```python
import pandas as pd
from alphastrategy.dsl.eval import evaluate_dsl, IllegalWeights

def test_equal_weight_two_symbols():
    bars = pd.DataFrame({"AAPL": [1.0, 1.0], "MSFT": [1.0, 1.0]},
                        index=pd.to_datetime(["2024-01-30", "2024-01-31"]))
    dsl = {"dsl_version": "alphaloop.dsl/v0", "universe": ["AAPL", "MSFT"],
           "steps": [{"op": "equal_weight"}]}
    w = evaluate_dsl(dsl, bars, pd.Timestamp("2024-01-31"), {})
    assert w == {"AAPL": 0.5, "MSFT": 0.5}

def test_unknown_op_raises():
    bars = pd.DataFrame({"AAPL": [1.0], "MSFT": [1.0]},
                        index=pd.to_datetime(["2024-01-31"]))
    dsl = {"dsl_version": "alphaloop.dsl/v0", "universe": ["AAPL", "MSFT"],
           "steps": [{"op": "not_a_real_op"}]}
    try:
        evaluate_dsl(dsl, bars, pd.Timestamp("2024-01-31"), {})
        assert False, "should have rejected unknown op"
    except (IllegalWeights, ValueError) as e:
        assert "not_a_real_op" in str(e)

def test_negative_weight_illegal():
    bars = pd.DataFrame({"AAPL": [1.0], "MSFT": [1.0]},
                        index=pd.to_datetime(["2024-01-31"]))
    dsl = {"dsl_version": "alphaloop.dsl/v0", "universe": ["AAPL", "MSFT"],
           "steps": [{"op": "clip", "params": {"max": -0.1}}]}
    try:
        evaluate_dsl(dsl, bars, pd.Timestamp("2024-01-31"), {})
        assert False, "negative weights must be illegal"
    except IllegalWeights:
        pass
```

- [ ] **Step 2: pytest — FAIL**

- [ ] **Step 3: Implement ops** listed in Global Constraints. Unknown op raises `ImportRejected` or `IllegalWeights` with the op name.

- [ ] **Step 4: PASS** including one test that `momentum_12_1` on a rising series produces a long weight then `normalize`.

- [ ] **Step 5: Commit** `feat: evaluate closed DSL v0 to target weights`

### Task 5: Sandbox worker + conformance gate on import

**Files:**
- Create: `src/alphastrategy/dsl/worker.py`
- Create: `src/alphastrategy/dsl/sandbox.py`
- Modify: `src/alphastrategy/bundle/import_bundle.py` (call sandbox on `conformance/`)
- Test: `tests/alphastrategy/test_sandbox.py`

**Interfaces:**
- Consumes: `evaluate_dsl`
- Produces: `run_sandbox(bundle_dir: Path, bars, effective_at: str, timeout_s: float = 5.0) -> dict[str, float]`

- [ ] **Step 1: Failing tests** — worker returns expected weights; timeout raises `HaltRequested`; weights off by `1e-5` fail import; extra asset fails.

Tolerance helper:

```python
def weights_match(got: dict[str, float], expected: dict[str, float]) -> bool:
    if set(got) != set(expected):
        return False
    for k, exp in expected.items():
        tol = max(1e-9, abs(exp) * 1e-6)
        if abs(got[k] - exp) > tol:
            return False
    return True
```

- [ ] **Step 2: pytest FAIL**

- [ ] **Step 3: Implement worker `if __name__ == "__main__"` reading stdin JSON. `import_asb` must run conformance after unpacking to a temp dir, then move to `imported/` only on success.

- [ ] **Step 4: PASS**

- [ ] **Step 5: Commit** `feat: sandbox DSL worker and conformance import`

### Task 6: Golden fixture checked in

**Files:**
- Create: `tests/alphastrategy/fixtures/golden/*.yaml` and `conformance/bars.csv`
- Create: `tests/alphastrategy/fixtures/golden.asb` (generated by a small script in the test or committed zip)
- Test: `tests/alphastrategy/test_golden_import.py`

- [ ] **Step 1: Test that `import_asb(golden.asb)` succeeds and records `imported` state**

- [ ] **Step 2–4: TDD until PASS**

- [ ] **Step 5: Commit** `test: add golden .asb fixture`

Phase 1 gate: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_bundle_hash.py tests/alphastrategy/test_bundle_import.py tests/alphastrategy/test_dsl_eval.py tests/alphastrategy/test_sandbox.py tests/alphastrategy/test_golden_import.py -v`

### Task 7: Live hard wall copy + order methods (mocked HTTP)

**Files:**
- Create: `src/alphastrategy/live/broker.py` (copy from `src/openstrategy/live/broker.py`, add protocol methods)
- Create: `src/alphastrategy/live/alpaca.py`
- Test: `tests/alphastrategy/test_safety.py`
- Test: `tests/alphastrategy/test_alpaca_paper.py`

**Interfaces:**
- Produces: `AlpacaAdapter` with existing safety plus `list_positions`, `place_order`, `cancel_order`, `close_all`, `get_clock`, `get_bars`

- [ ] **Step 1: Port `tests/live/test_safety.py` assertions onto `alphastrategy.live`. Add `test_place_order_posts_market_day` with `urllib.request.urlopen` monkeypatch. Add `test_place_order_not_called_in_this_test_file_against_real_network` by asserting the mock was used.

- [ ] **Step 2: FAIL then implement `_request` supporting GET/POST/DELETE like the existing adapter (extend the current GET-only `_request`).

- [ ] **Step 3: `paper=True` default; live still raises without `confirm_live=True`.

- [ ] **Step 4: PASS**

- [ ] **Step 5: Commit** `feat: paper Alpaca adapter with orders behind hard wall`

### Task 8: Combine allocations + risk merge

**Files:**
- Create: `src/alphastrategy/supervisor/combine.py`
- Create: `src/alphastrategy/risk/policy.py`
- Create: `src/alphastrategy/risk/check.py`
- Test: `tests/alphastrategy/test_combine.py`
- Test: `tests/alphastrategy/test_risk.py`

**Interfaces:**
- Produces: `combine(sleeves: list[tuple[float, dict[str, float]]]) -> dict[str, float]`; `AccountPolicy.defaults()`; `merge_limits(envelope: dict, account: AccountPolicy, overlay: dict | None) -> AccountPolicy` (overlay may only min() caps); `check_book(combined, equity, policy) -> None` raises `FlattenRequested("account")` on breach

- [ ] **Step 1: Tests** — `0.4*{A:1} + 0.6*{B:1} => {A:0.4,B:0.6}`; allocation sum `1.1` raises `ValueError`; overlay increasing `max_name_weight` raises `ImportRejected` or `ValueError`; gross 1.2 equity 1.0 flattens.

- [ ] **Step 2–4: TDD**

- [ ] **Step 5: Commit** `feat: sleeve combine and tighten-only risk`

### Task 9: Clock events

**Files:**
- Create: `src/alphastrategy/supervisor/clock.py`
- Test: `tests/alphastrategy/test_clock.py`

**Interfaces:**
- Produces: `ClockSnapshot`, `next_rebalance_event(...) -> str | None`

- [ ] **Step 1: Tests** — open event only after 3 minutes; no double open; close event inside 12 minutes; heartbeat snapshots with `is_open` unchanged return `None`.

- [ ] **Step 2–4: TDD**

- [ ] **Step 5: Commit** `feat: session open/close rebalance clock`

### Task 10: Order mapping + deviation

**Files:**
- Create: `src/alphastrategy/supervisor/orders.py`
- Test: `tests/alphastrategy/test_orders.py`

**Interfaces:**
- Produces: `plan_orders(combined, positions, prices, equity, policy) -> list[OrderPlan]`; `OrderPlan(symbol, qty, side)`; skip below min delta; `deviations_after(wanted: dict, got: dict, equity, prices) -> list[dict]`

- [ ] **Step 1–4: TDD with a fake broker capturing `place_order` calls. Never instantiate a live adapter.

- [ ] **Step 5: Commit** `feat: map target weights to paper market orders`

### Task 11: Audit log redaction

**Files:**
- Create: `src/alphastrategy/supervisor/audit.py`
- Test: `tests/alphastrategy/test_audit.py`

- [ ] **Step 1: Test that `audit.append(path, {"event": "order", "api_key": "PK_SECRET", "symbol": "AAPL"})` writes JSONL without `PK_SECRET`.

- [ ] **Step 2–4: TDD**

- [ ] **Step 5: Commit** `feat: append-only audit log with secret redaction`

### Task 12: Supervisor loop halt vs flatten

**Files:**
- Create: `src/alphastrategy/supervisor/state.py`
- Create: `src/alphastrategy/supervisor/loop.py`
- Test: `tests/alphastrategy/test_halt_flatten.py`

**Interfaces:**
- Produces: `class Supervisor` with `tick()`, `start_sleeve(bundle_id, allocation)`, `stop_sleeve`, `kill_sleeve`, `kill_account`, `resume()`. States: `starting`, `idle_out_of_session`, `idle_in_session`, `rebalancing`, `halted`, `flattening`, `stopped`.

- [ ] **Step 1: Tests with a FakeBroker** (in-memory positions, clock, bars):

  - simulated open → one `place_order` batch, `last_rebalance_event` set
  - second tick same session → no orders
  - `FakeBroker.raise_on_get_bars = True` → state `halted`, no flatten
  - `kill_account` while broker up → `close_all` called, state `stopped` or idle flat
  - `resume` after halt does not call `place_order` until next event

- [ ] **Step 2–4: TDD**

- [ ] **Step 5: Commit** `feat: supervisor halt and flatten matrix`

Phase 2 gate: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -k "not api and not cli and not e2e and not web" -v`

### Task 13: HTTP handlers (no UI)

**Files:**
- Create: `src/alphastrategy/api/handlers.py`
- Create: `src/alphastrategy/api/app.py`
- Test: `tests/alphastrategy/test_api.py`

**Interfaces:**
- Produces: `make_server(home, supervisor, bind="127.0.0.1", port=7460)`; handlers as in §A.9

- [ ] **Step 1: Use `http.client` against `make_server` on port 0. Test import 400 on bad zip; paper/start 409 when allocations would exceed 1; GET `/api/status`; **no** JSON field `paper: false` setter.

```python
def test_start_rejects_allocation_sum_over_one(api_client):
    r = api_client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.7})
    r2 = api_client.post("/api/paper/start", json={"bundle_id": "asb_y", "allocation": 0.4})
    assert r2.status == 409
```

- [ ] **Step 2–4: TDD**

- [ ] **Step 5: Commit** `feat: localhost JSON control-plane API`

### Task 14: CLI verbs

**Files:**
- Create: `src/alphastrategy/cli/main.py`
- Create: `src/alphastrategy/__main__.py`
- Test: `tests/alphastrategy/test_cli.py`

**Interfaces:**
- Produces: `main(argv: list[str] | None) -> int` with commands `start`, `import`, `paper start|stop|kill|resume`, `status`

- [ ] **Step 1: Tests via `main(["import", str(golden)])`. Assert `main(["paper", "start", "--live"])` or `--confirm-yes-i-know-what-im-doing` returns non-zero and does not construct live adapter (patch `AlpacaAdapter`).

- [ ] **Step 2–4: TDD** argparse subcommands calling the same functions as HTTP handlers.

- [ ] **Step 5: Commit** `feat: alphastrategy CLI for import and paper control`

### Task 15: Quiet cockpit static shell

**Files:**
- Create: `src/alphastrategy/web/static/index.html`
- Create: `src/alphastrategy/web/static/styles.css`
- Create: `src/alphastrategy/web/static/app.js`
- Test: `tests/alphastrategy/test_web_tokens.py`

- [ ] **Step 1: Test reads CSS/HTML from disk and asserts the locked hex tokens and five nav labels (`Portfolio`, `Strategies`, `Run`, `Activity`, `Risk`). Assert HTML contains no `confirm_live`, no `paper=false`, no “Live” toggle.

- [ ] **Step 2–4: Implement the SPA: fetch `/api/*`, render tabular numbers, halt banner class `.halt` using `#f59e0b`.

- [ ] **Step 5: Commit** `feat: quiet cockpit web shell`

### Task 16: Wire static files into `alphastrategy start`

**Files:**
- Modify: `src/alphastrategy/api/app.py`
- Modify: `src/alphastrategy/cli/main.py`
- Test: `tests/alphastrategy/test_api.py` (GET `/` returns HTML)

- [ ] **Step 1–4: Serving `index.html` at `/` and assets under `/static/`. Bind default `127.0.0.1`. Test that passing `--host 0.0.0.0` in v1 is either rejected or documented as opt-in; **default must remain localhost**.

- [ ] **Step 5: Commit** `feat: serve cockpit from alphastrategy start`

Phase 3 gate: API + CLI + token tests PASS.

### Task 17: Identity cut and README

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `src/alphastrategy/__init__.py` (already 0.1.0)
- Test: `tests/alphastrategy/test_packaging.py`

- [ ] **Step 1: Failing test that `pyproject.toml` contains `name = "alphastrategy"`, `version = "0.1.0"`, `[project.scripts] alphastrategy =`, and does **not** list `openstrategy =` as a script. README contains “paper” and “alphaloop” and does not promise alpha.

- [ ] **Step 2–4: Update metadata, URLs to `https://github.com/AlphaStrategyAI/alphastrategy`. Set hatch `packages = ["src/alphastrategy"]`. Leave `src/openstrategy/` on disk unshipped.

- [ ] **Step 5: Commit** `chore: ship alphastrategy 0.1.0 identity`

### Task 18: Mocked end-to-end gate

**Files:**
- Test: `tests/alphastrategy/test_e2e_mocked.py`

- [ ] **Step 1: One test `test_v1_done_path` using golden `.asb` + FakeBroker:

  1. `import_asb`
  2. `start_sleeve(allocation=0.4)`
  3. force open rebalance → orders recorded
  4. force limit breach → flatten
  5. new run: disconnect halt → no flatten
  6. `kill_account` → flatten
  7. `audit.jsonl` contains `import`, `rebalance`, `halt`, `flatten` and no credential strings
  8. `/api/portfolio` JSON includes a halt or deviation field that is not empty when halted

- [ ] **Step 2–4: Fix gaps until PASS**

- [ ] **Step 5: Commit** `test: mocked v1 import-start-rebalance-halt-flatten path`

**Product gate command:**

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -v
```

Expected: all PASS. Zero real network orders.

---

## C. Spec coverage checklist

| Requirements section | Tasks |
| --- | --- |
| §1–2 positioning, hard walls | 7, 14, 17 |
| §3–4 `.asb`, hash, FOUND, conformance | 2, 3, 5, 6 |
| §4.3 DSL v0 closed ops | 4, 5 |
| §5 sleeves + combine | 8, 12 |
| §6 session loop | 9, 12 |
| §7 halt vs flatten, limits | 8, 12 |
| §8 Quiet cockpit Web | 15, 16 |
| §9 CLI | 14 |
| §10 broker methods | 7, 10 |
| §11 identity cut | 17 |
| §12 v1 done | 18 |
| §13 verification | 2–18 tests |

No requirement is deferred except alphaloop’s own `export` producer (golden fixtures stand in, as specified).
