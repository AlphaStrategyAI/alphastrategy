# alphastrategy v1 product requirements

**Date:** 2026-08-19
**Status:** Requirements (moved from `docs/superpowers/specs/`)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Historical freeze:** git tag `v1.1.3` = `41cbdff78d12080f82d1e61790df33e92ea29540` (openstrategy honest-tool snapshot, pre-alphaloop rename)
**Technical design:** [`docs/plans/2026-08-19-alphastrategy-v1-technical-design.md`](../plans/2026-08-19-alphastrategy-v1-technical-design.md)

This document is the product contract for alphastrategy. Implementation follows the technical design in `docs/plans/`.

## 1. Positioning

alphaloop **searches and stress-tests** candidate strategies. It does not promise that a passing candidate will make money.

alphastrategy **runs** qualified candidates as paper (v1) and later live (out of v1) execution. It does not invent strategies, does not run the six diagnostic questions, and does not produce factors.

One-way handoff:

```text
alphaloop FOUND candidate
    --(human export)--> strategy.asb
    --(human import)--> alphastrategy imported
    --(human promote)--> paper sleeves
```

alphastrategy does not send fills, PnL, drift, or other telemetry back to alphaloop.

Public story:

- alphaloop: overnight research lab; conclusion is `FOUND` / `NO_EVIDENCE` / `INCONCLUSIVE`.
- alphastrategy: local paper trading desk; conclusion is positions, orders, deviations, halt/flatten.

The current tree is still the openstrategy v1.1.3 research library (`src/openstrategy`, Streamlit, `openstrategy report`). v1 of this product replaces that identity with an execution runtime. Tag `v1.1.3` remains the last honest-tool snapshot.

## 2. Identity and hard walls

Package name: `alphastrategy`. CLI: `alphastrategy`. Web: local control plane.

Hard walls:

1. Default and v1-only trading venue is Alpaca **paper** (`https://paper-api.alpaca.markets`).
2. Live construction still requires `paper=False` and `confirm_live=True` (`confirm_yes_i_know_what_im_doing`). v1 CLI and Web **must not expose** a live control.
3. No broker credentials in `.asb` files, logs, or the Web UI.
4. Strategy logic never sees secrets, network, or the broker object.
5. Import is not permission to trade. Paper start is a second explicit human action.
6. alphastrategy never calls alphaloop execution APIs (alphaloop has none) and never auto-promotes a bundle.

Market profile v1: only `us-equity-daily`. `crypto-daily` and unknown profiles fail closed.

## 3. Alignment with alphaloop

### 3.1 Source of truth

alphaloop `docs/requirements/product-positioning-requirements.md` (2026-08-18) defines the producer side:

- Export only `FOUND` candidates, human-triggered: `alphaloop export <candidate_id> --output strategy.asb`.
- Archive contains no arbitrary executable code.
- DSL outputs broker-neutral target weights: `effective_at -> {asset_id: target_weight}`.
- AlphaStrategy maps weights to orders; if the target cannot be reached, record execution deviation; do not change the strategy definition.

### 3.2 What alphaloop code does today (do not consume)

The running alphaloop loop still persists `top5.json` rows of `{strategy class name, factor, params}` and Python `BaseStrategy.generate_signals`. That is **not** a legal alphastrategy input. Only `.asb` is.

Until `alphaloop export` exists, this repo ships golden `.asb` fixtures for import, conformance, supervisor, and Web tests.

### 3.3 Shared versions

alphastrategy pins a support table of `(schema_version, dsl_version)`. Unknown pairs fail closed. New DSL operators require a `dsl_version` bump in both repos. alphastrategy does not invent a second DSL.

## 4. Strategy Candidate Bundle (`.asb`)

### 4.1 Archive

- File extension `.asb`.
- Zip of a fixed member whitelist. No directory traversal. No `.py`, no native executables, no credentials.
- Content hash is SHA-256 over **uncompressed member bytes** in sorted path order, excluding `bundle.yaml` itself (hash is recorded inside `bundle.yaml`). `bundle_id` is derived from that hash.
- Any byte change is a new bundle. There is no in-place edit.

Members:

| Path | Consumer use |
| --- | --- |
| `bundle.yaml` | `schema_version`, `dsl_version`, `bundle_id`, `content_hash`, created time; optional `registry_uri` (v1 ignores, never fetches). |
| `strategy.dsl.yaml` | Closed-operator strategy. Sole definition of target weights. |
| `market-profile.yaml` | v1 accepts only `us-equity-daily`. |
| `parameters.yaml` | Frozen parameters. Interpreter reads only this file, never env vars. |
| `risk-envelope.yaml` | Research-side caps. Missing fields default to the strictest v1 account defaults, never to unlimited. |
| `lineage.yaml` | `run_id`, candidate id, engine/data hashes, `research_outcome`. Must be `FOUND`. |
| `evidence/` | Hard-gate materials present; declared `passes_all: true`. alphastrategy does **not** recompute DSR. |
| `conformance/` | Frozen bars + expected target weights. Interpreter output must match: each asset within abs `1e-9` or rel `1e-6` (larger wins); extra or missing assets fail. |

### 4.2 Import pipeline (fail closed, no orders)

1. Unpack to an isolated directory; reject unknown members.
2. Recompute content hash; mismatch rejects.
3. `(schema_version, dsl_version)` not in support table rejects.
4. Lineage/evidence/`FOUND`/`passes_all` checks.
5. Run `conformance/` inside the sandbox. Unknown operator, timeout, memory cap, attempted I/O, or weight mismatch (same tolerance as the table above) rejects.
6. Store under `imported/<bundle_id>/`. State is `imported`, not `paper`.

CLI: `alphastrategy import path.asb`. Web upload uses the same pipeline.

### 4.3 DSL v0 (consumer constraints)

- Closed operators only. v0 catalog is the ten existing openstrategy/alphaloop factors plus portfolio primitives: `rsi`, `macd`, `roc`, `momentum_12_1`, `bollinger_zscore`, `ohlr_4_pct`, `pairs_spread`, `atr_breakout`, `parkinson_hist_vol`, `obv_slope`, `normalize`, `clip`, `equal_weight`, `cash`.
- No `eval`, `import`, custom functions, or operator plugins.
- Output: finite assets, finite numbers, long-only (no negative weights in v1), residual cash allowed, weights sum to 1. NaN, Inf, undeclared assets, or shorts are illegal output.
- Illegal output is a **health halt** (dirty data): stop new orders, do not flatten.

Canonical YAML grammar for these operators is shared with alphaloop under the same `dsl_version`. Until that file exists in alphaloop, golden fixtures in this repo define the v0 documents both tests consume.

## 5. Runtime architecture

One Alpaca paper account. Multiple bundles cannot each place orders or they will fight the same positions.

```text
Web / CLI
    |
    v
Local control plane (localhost)
    |
    v
Supervisor  <-- sole holder of Alpaca keys and sole order placer
    |
    +-- sleeve interpreters (one sandbox process per running bundle)
```

- Each running bundle is a **sleeve**: isolated DSL interpreter, allocation fraction, per-sleeve risk overlay.
- Supervisor is the only process that talks to Alpaca.
- Combined target:

```text
combined[asset] = Σ_i allocation_i * weight_i[asset]
```

`Σ allocation_i <= 1`. Residual is cash. Bundles not in `paper` have allocation 0.

- If the combined target cannot be achieved, log `execution_deviation`. Do not rewrite DSL, parameters, or allocations silently.
- Stopping a sleeve sets its target contribution to 0 on the next legal rebalance (unless Kill, see §7).
- Interpreters receive bars + `effective_at` + frozen parameters. They never receive keys, positions, or a broker handle.
- Sandbox: subprocess, stdin/stdout JSON only, no env secrets, no network, no filesystem besides the unpacked bundle, 5s wall clock, 512MB memory.

## 6. Session loop

Clock source of truth: Alpaca `GET /v2/clock` (`is_open`, `next_open`, `next_close`).

Heartbeat every **20s**: health, reconciliation, audit. Heartbeat does **not** rebalance and does **not** place orders.

Regular rebalance at most twice per session:

- **Open:** after `is_open` false→true, wait **3 minutes**, then one rebalance. Persist `last_rebalance_event` so it cannot fire twice.
- **Close:** in the window **12 minutes** before `next_close`, one rebalance.

`effective_at` is the timestamp of the last complete bar used for that event.

One rebalance:

1. Fetch account, positions, and Alpaca bars for the union of sleeve universes (same venue as orders).
2. If bars are stale, broker unreachable, or clock says trading is unexpected: **health halt** (no new orders, do not flatten).
3. For each running sleeve, evaluate DSL in sandbox. Illegal weights or sandbox failure: health halt (account-level; do not flatten on garbage).
4. Combine allocations; apply `min(account policy, each sleeve envelope)` (stricter wins) to the combined book and to each sleeve's implied notionals.
5. Skip deltas below `max($1, 0.1% of equity)`.
6. Place **RTH paper market orders** only (no pre/post-market, no options, no limit/stop types in v1).
7. Record targets, order ids, fills, deviations in append-only JSONL. Never log secrets.

Supervisor states: `starting`, `idle_out_of_session`, `idle_in_session`, `rebalancing`, `halted`, `flattening`, `stopped`.

Closing the browser or CLI does not stop the supervisor. Host sleep/power-off does.

## 7. Risk and kill

Two layers, stricter wins. Interpreters never see the broker.

**A. Bundle `risk-envelope.yaml`** — research caps.

**B. Account / runtime policy** — operator config, not inside `.asb`. v1 defaults (may tighten; loosening requires explicit config):

| Limit | Default |
| --- | --- |
| Direction | Long only |
| Gross notional | ≤ 100% of equity |
| Single-name weight | ≤ 20% |
| Name count | ≤ 50 |
| Single order notional | ≤ 20% of equity |
| Orders per rebalance | ≤ 100 |
| Orders per trading day | ≤ 200 |
| Min rebalance delta | `max($1, 0.1% equity)` |

Per-sleeve Web/CLI overlays can only **tighten** A∩B, never loosen below envelope or account defaults.

Triggers:

| Trigger | Action |
| --- | --- |
| Manual account kill, SIGTERM, SIGINT | If Alpaca reachable: cancel open orders and flatten the **whole** paper account |
| Manual sleeve kill | If reachable: flatten that sleeve’s implied positions (combined book minus that sleeve); if that cannot be isolated cleanly, flatten whole account rather than guess |
| Limit breach (A or B) | Same as account kill if reachable |
| Disconnect, stale bars, unexpected session, illegal DSL output, sandbox death | **Halt**: no new orders, do not flatten |

Halt is not flatten. Resume requires explicit `paper resume` (CLI or Web). Resume does **not** fire a catch-up rebalance; the next legal open/close event does.

## 8. Web control plane (primary operator surface)

Visual system: **Quiet cockpit** (locked).

- Background `#0b0e14`, surface `#11151d`, border `#2a3142`, text `#e5e9f0`, muted `#5c6573` / `#9ba3b4`.
- Running `#10b981`, halt/warn `#f59e0b`, kill/fail `#ef4444`.
- UI sans (system-ui), tabular numerals, dense numbers but sparse chrome.
- Same night palette family as alphaloop Quant Lab, **different job**: positions, sleeves, clock, deviations — not DAG / top-5 / radar.

`alphastrategy start` binds the control plane to **localhost** by default and starts the supervisor. No public bind in v1. No multi-user auth in v1.

Five screens in one shell:

1. **Portfolio** (home) — equity, cash, day PnL, gross, combined positions, sleeve contribution, RTH countdown, next rebalance, halt/deviation banners that cannot be visually quiet.
2. **Strategies** — imported `.asb` list: state (`imported` / `paper` / `halted` / `stopped`), allocation, risk summary. Upload runs import. Failures are readable (hash, schema, conformance).
3. **Run** — per sleeve: set allocation, tighten risk, explicit confirm to start paper. **Stop** waits for the next rebalance to zero that sleeve. **Kill** flattens per §7. Account kill is separate and louder.
4. **Activity** — time-ordered rebalances, target vs fill, deviations, halt/flatten. Drill into one event.
5. **Risk** — account totals at top (always visible); per-sleeve caps and allocation. UI must refuse values looser than envelope.

Web must not: strategy code editor, backtest, diagnostics, live toggle, disable the paper hard wall, or call alphaloop.

## 9. CLI (secondary)

Required verbs:

- `alphastrategy start` — control plane + supervisor
- `alphastrategy import <file.asb>`
- `alphastrategy paper start --bundle <id> --allocation <0-1>`
- `alphastrategy paper stop --bundle <id>`
- `alphastrategy paper kill [--bundle <id>]` (omit bundle = account kill)
- `alphastrategy paper resume`
- `alphastrategy status`

v1 CLI rejects any live flag combination that would construct a non-paper adapter.

## 10. Broker adapter

Extend the existing `Broker` protocol (today: `get_account`, `is_market_open`) with `list_positions`, `place_order`, `cancel_order`, `close_all`. Keep `_enforce_safety` at construct time.

v1 supervisor only ever constructs paper. Tests mock HTTP; they never hit the real Alpaca network.

Market data for weight calculation is Alpaca only (same account/venue as orders). Yahoo, AKShare, CCXT, and OpenBB are not part of this product.

## 11. Repository shape after the identity cut

Leave `v1.1.3` history intact. New work does not keep research modules on the main path:

- Remove or stop shipping as product: `openstrategy.diagnostic`, `openstrategy.engineer` factor research, `openstrategy report`, Streamlit UI, multi-source data adapters.
- Replace package `openstrategy` with `alphastrategy`.
- New modules (names indicative): bundle import/hash, DSL sandbox interpreter, supervisor/sleeves, Alpaca paper execution, audit log, local HTTP API, packaged Web cockpit.
- Golden `.asb` fixtures live in-tree for tests.

New version line starts at execution-product `0.1.0`. Do not pretend this is openstrategy 1.1.4.

## 12. v1 in / out

**In**

- Quiet-cockpit Web desk + localhost control plane
- `.asb` import and conformance
- Supervisor, sleeves, allocations summing to ≤ 100%
- Alpaca paper, `us-equity-daily`, RTH session rebalance
- Account and per-sleeve risk, halt vs flatten as specified
- Audit JSONL
- Golden bundles (alphaloop export not required to start)

**Out**

- Live money, crypto profile, pre/post-market, options, shorts
- Python inside bundles, re-running diagnostics, WebSockets
- Strategy-level stops beyond envelope/account caps
- Telemetry to alphaloop, Bundle Registry, team auth, MCP, desktop wrapper
- Auto catch-up orders after halt
- Mutating strategy definition when execution misses the target
- Public network bind

**v1 done when:** using only golden bundles and mocked Alpaca, a test (and a human on the Web) can: import → set allocations → paper start → simulated open/close rebalance → limit flatten → disconnect halt → kill flatten, with audit lines for each, and Portfolio shows halt/deviation instead of a green dashboard.

## 13. Verification

- Hash/tamper tests reject modified `.asb`.
- Unsupported schema/DSL fail closed.
- Conformance fixtures: expected weights byte-or-tolerance equal.
- Negative tests: missing evidence cannot import; `passes_all: false` cannot import; `.py` member cannot import.
- Supervisor tests: combined weights, allocation residual cash, no double rebalance in one event, halt vs flatten matrix.
- Safety tests: live constructor still refused without double opt-in; v1 entry points never construct live; no secrets in audit logs.
- Web tests: import error copy, allocation > 100% rejected, risk loosen rejected, paper wall not togglable.
- No test places a real order.

## 14. Implementation decomposition

Work is specified in [`docs/plans/2026-08-19-alphastrategy-v1-technical-design.md`](../plans/2026-08-19-alphastrategy-v1-technical-design.md), split into four independently testable phases:

1. Bundle schema, hash, import, golden fixtures, DSL v0 interpreter + sandbox.
2. Supervisor, clock, combine-and-order, halt/flatten, Alpaca paper adapter extensions.
3. Local control-plane API + Quiet cockpit Web (five screens).
4. Identity cut: package rename, drop research product path, README.

Item 1 is the contract both this repo and alphaloop export must share. Coordinate `dsl_version` with alphaloop rather than forking it here.
