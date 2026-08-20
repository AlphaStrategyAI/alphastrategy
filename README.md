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
separate, explicit human action.

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
├── web/static/   # Quiet cockpit (Portfolio, Strategies, Run, Activity, Risk)
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
screen) loads the same operator runbook as `alphastrategy help`.

Portfolio is the home screen: RTH countdown to the next legal
rebalance, sleeve contribution, and **wanted vs got** weights. A
flattened account shows a red **FLAT** banner; it must not look like
an idle empty book.

---

## Operator

- **Halt** stops new orders and does not flatten. `paper resume` does
  not catch up; the next legal open/close rebalance does.
- **Account kill** flattens the whole paper account. On the Web, type
  `FLATTEN` and confirm. CLI: `alphastrategy paper kill` (omit
  `--bundle`).
- **Sleeve kill** (`paper kill --bundle <id>`) trades to the residual
  book when last targets and an open session make isolation clean;
  otherwise it flattens the whole account rather than guess.
- Daily paper orders are capped (default 200). Overflow is a limit
  flatten, not a partial batch.
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
