# alphastrategy

Local **paper** execution desk for strategy bundles exported from
[alphaloop](https://github.com/AlphaStrategyAI/alphaloop).

alphastrategy imports alphaloop `.asb` archives, evaluates the closed
DSL in a sandbox, and runs sleeves on Alpaca **paper** only. A single
**Supervisor** process is the only component that places orders.

This is an execution runtime, not a research lab. It does not invent
strategies, run diagnostics, or send telemetry back to alphaloop.

---

## Workflow

```text
alphaloop FOUND candidate
    --(human export)--> strategy.asb
    --(human import)--> alphastrategy imported
    --(human promote)--> paper sleeves
```

1. Research and stress-test candidates in **alphaloop**.
2. Export a `FOUND` candidate: `alphaloop export <candidate_id> --output strategy.asb`.
3. Import into alphastrategy: `alphastrategy import strategy.asb`.
4. Start the control plane and open the Quiet cockpit in your browser.
5. Promote a bundle to a paper sleeve when you are ready to trade.

Import is not permission to trade. Starting a paper sleeve is a
separate, explicit human action. Import failures name the gate
(hash, schema, conformance) and a next action.

Docs map: [docs/index.md](docs/index.md). Runtime explanation:
[docs/explanation/architecture.md](docs/explanation/architecture.md).

---

## Quick start

```bash
# Install (Python 3.9+)
git clone https://github.com/AlphaStrategyAI/alphastrategy.git
cd alphastrategy
pip install -e ".[dev]"

# Import a bundle from alphaloop
alphastrategy import path/to/strategy.asb

# Start the localhost control plane (Quiet cockpit at http://127.0.0.1:7460)
alphastrategy start

# Promote to a paper sleeve (requires running control plane)
alphastrategy paper start --bundle <bundle_id> --allocation 0.4
```

Set `ALPACA_API_KEY` and `ALPACA_API_SECRET_KEY` for paper trading. v1
defaults to `https://paper-api.alpaca.markets` and exposes no live
trading controls in the CLI or web UI.

---

## Architecture

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

Why one Supervisor, why paper-only, and C4 context/container diagrams:
[docs/explanation/architecture.md](docs/explanation/architecture.md).

```text
alphastrategy/
├── bundle/       # .asb import, hash, conformance
├── dsl/          # closed-operator sandbox (alphaloop.dsl/v0)
├── supervisor/   # session loop; sole order placer
├── live/         # Alpaca paper adapter (hard-walled)
├── api/          # localhost control plane
├── web/static/    # Quiet cockpit HTML/CSS
├── web/static/js/ # screen-shaped parts; GET /app.js assembles them
├── helptext.py   # operator runbook (CLI, GET /api/help, cockpit Help)
└── cli/          # alphastrategy command
```

Strategy sleeves return target weights over stdin/stdout JSON. The
Supervisor combines sleeves, enforces risk limits, and places paper
orders through Alpaca. Strategy code never sees broker credentials.

---

## Quiet cockpit

`alphastrategy start` serves a single-page web desk at
`http://127.0.0.1:7460` (localhost only in v1). The Quiet cockpit
shows portfolio state, running sleeves, activity, and risk — not
backtests or strategy editing. **Help** (header control, not a sixth
screen) loads a how-to for the **current screen**. Help starts with
**Your first paper session**, then that screen how-to and the jobs for
the screen. **Full runbook** is
the six runbook sections. `alphastrategy help` prints **Your first paper
session** first, then **How to** jobs, then screen how-tos, then those
same sections. F1 shows the lesson plus the jobs for the
current screen (import, start paper, flatten, tighten, wanted versus got).
Header hint: **Alt+1–5** switches screens; **F1** toggles Help.
The header **LIVE / STALE / DEAD** pulse is the Supervisor beat
(every 20s, no orders), not RTH Session OPEN/CLOSED.

Portfolio is three bands: **Book** (Equity is the hero, with Cash, Day PnL,
and **Drift**), **Flatten budgets** (Gross, Names, Orders today), and
**Clock** (**Session / Now / Next / Last**; Next is the hero), then
**Positions** (**Rows / Wanted / Got / At cap**; Wanted is the hero) and
**Sleeves**.
Strategies is three bands: **Inventory** (Imported / Paper / Halted / Stopped;
Paper is the hero), **Import .asb**, and **Roster**. Import is not permission
to trade; start paper on Run.
Run is four bands: **Start paper**, **Sleeves** (Remaining / Spoken / Active /
Idle; Remaining is the hero), **After halt**, and **Flatten account**.
Positions and Sleeves sit side by side on a wide desk. Positions add a
**Cap** rail against the single-name limit. **Names** and **Orders today**
show remaining flatten budgets. **Cash** shows invested versus residual
against the last combined target. Sleeves show how much of the paper book
is spoken for. An empty Portfolio shows **Start this paper desk** as the
first glance band, then Book / Flatten budgets / Clock. Positions include
wanted names with no fill and a **Book** bar (wanted vs got). **Book Drift**
counts names off the last combined target. Gross
shows utilization against the account cap. Sleeve overlays is
**Spoken / Overlays / Tighter / Idle** (Spoken is the hero). Allocation
is a rail, not only text. Each overlay card is allocation rail and
tighter count; **Tighten this sleeve** holds the form. **Tighten this
sleeve stays open across the refresh** until you close it. A flattened account shows a red **FLAT** banner; it must not
look like an idle empty book. `alphastrategy status` includes `utilization`.
Risk names caps in desk words (**Gross cap**, **Names**, **Orders today**).
Tighten still posts the policy keys.
Risk is four bands: **Caps**, **Headroom**, **Tighten**, and **Sleeve overlays**.
Caps is **Gross cap / Name cap / Names / Orders today** (Gross cap is the hero).
Headroom is **Names / Orders today / Cash / Target cash** (Names is the hero).
Caps and Headroom stay sticky. Tighten is **Tight / Delta $ / Delta % / Fields**
(Tight is the hero), then groups **Gross / Names / Orders / Deltas**.
Activity is three bands: **Beat** (Pulse / Age / Interval / Supervisor;
Pulse is the hero), **Tape** (Rebalances is the hero), and **Blotter**.
Expanding a blotter row shows **Wanted / Got**, not a JSON dump.

---

## Operator

- **Halt** stops new orders and does not flatten. `paper resume` does
  not catch up; the next legal open/close rebalance does. Resume is only
  after halt. Persist-before-send flushes the snapshot to disk before
  orders so a host kill still sees interrupted rebalancing, flattening,
  or sleeve isolate. Audit and runtime overlays flush to disk with that
  snapshot family.
- **Account kill** flattens the whole paper account, clears the last book,
  and zeros live sleeves. **Start paper after flatten** starts the session
  loop again and does not catch up. On the Web, flatten lives
  under **Flatten account** (type `FLATTEN` and confirm). **Resume after
  halt** lives under **After halt**, not beside flatten. CLI:
  `alphastrategy paper kill` (omit `--bundle`) types `FLATTEN` on a TTY,
  or pass `--force` when stdin is not a TTY.
- **Sleeve kill** (`paper kill --bundle <id>`) trades to the residual
  book when last targets and an open session make isolation clean;
  otherwise it flattens the whole account rather than guess. The CLI
  prints JSON (`isolated` vs `flattened`). A desk banner reports the
  same outcome.
- Heartbeat every 20s does not place orders. Header **LIVE / STALE /
  DEAD** is the Supervisor beat, not RTH session. Header **OPEN / CLOSED**
  is the RTH session. Spoken Supervisor is the runtime state. `status`
  includes `heartbeat`.
- Halt, flatten, deviation, control-plane, and sleeve-kill banners stay
  visible on every screen, not only Portfolio.
- Activity kill rows say **isolated residual** or **flattened account**.
  `alphastrategy status` includes `last_kill` even if the desk is down.
- Daily paper orders are capped (default 200). Overflow is a limit
  flatten, not a partial batch. The flatten banner names the breached cap.
- Same runbook: `alphastrategy help`, `GET /api/help`, cockpit Help.

---

## Hard walls

- Alpaca **paper** is the only trading venue in v1.
- No live toggle in CLI or web UI.
- No broker credentials in `.asb` files, logs, or the web UI.
- alphastrategy never calls alphaloop APIs and never auto-promotes a bundle.

---

## Tests

```bash
PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -v
```

---

## Historical note

Git tag `v1.1.3` (`41cbdff78d12080f82d1e61790df33e92ea29540`) is the
last openstrategy honest-tool snapshot. The `src/openstrategy/` tree
remains in the repository for history but is not packaged or shipped as
part of alphastrategy.

---

## License

MIT. See [LICENSE](LICENSE).
