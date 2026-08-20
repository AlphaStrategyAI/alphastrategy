# AGENTS.md

## Cursor Cloud specific instructions

alphastrategy is a local **Alpaca paper** execution desk (`src/alphastrategy`, `hatchling` build). It imports alphaloop `.asb` bundles, evaluates a closed DSL in a sandbox, and places paper orders through a single **Supervisor**. It is not a research lab.

Do not grow `src/openstrategy/`. That tree is historical (git tag `v1.1.3`) and is not packaged. The product CLI is `alphastrategy`, not `openstrategy`.

### Environment

- A virtualenv lives at `.venv` (gitignored). Activate it with `source .venv/bin/activate` before running anything.
- `python3 -m venv` requires the system package `python3.12-venv` (already provisioned in the base image).
- Package extra for work in this repo: `pip install -e ".[dev]"`.

### Test / lint / run commands

- Product tests (never hit a real broker):

  ```bash
  PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -v
  ```

- Do not use `tests/integration/` Yahoo/AKShare/CCXT/OpenBB jobs as alphastrategy acceptance. Those belong to the unpackaged research tree.
- Lint tools may exist; do not treat pre-existing findings under `src/openstrategy/` as regressions from alphastrategy work.
- Control plane + Quiet cockpit: `alphastrategy start` binds `http://127.0.0.1:7460` (localhost only). Paper credentials: `ALPACA_API_KEY` and `ALPACA_API_SECRET_KEY`. v1 exposes no live trading control.
- Operator runbook: `alphastrategy help` (same copy as in-desk Help). Product contract: `docs/requirements/2026-08-19-alphastrategy-v1-requirements.md`. Runtime explanation: `docs/explanation/architecture.md`. Docs map: `docs/index.md`.
