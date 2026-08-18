# AGENTS.md

## Cursor Cloud specific instructions

OpenStrategy is a pure-Python quantitative-research library (`src/openstrategy`, `hatchling` build) with three ways to exercise it: a `pytest` test suite, an `openstrategy` CLI, and an optional Streamlit WebUI. Everything runs fully offline on synthetic data — no API keys or network access are required for the default flows.

### Environment
- A virtualenv lives at `.venv` (gitignored). Activate it with `source .venv/bin/activate` before running anything. The startup update script recreates/refreshes it automatically.
- `python3 -m venv` requires the system package `python3.12-venv` (already provisioned in the base image; only relevant if rebuilding from scratch).
- The package is installed editable with the `dev,analysis,optimization,crypto,china` extras plus `streamlit` (streamlit is intentionally *not* in `pyproject.toml` — it is a soft/optional dependency for the WebUI only). Installed pandas/numpy are newer majors (pandas 3.x, numpy 2.x) than the `>=` floors in `pyproject.toml`; all unit tests still pass.

### Test / lint / run commands
- Tests: `python -m pytest tests/` — 190 pass, 12 skip. Skips are expected: integration tests under `tests/integration/` only run with `OPENSTRATEGY_INTEGRATION=1` (they hit live Yahoo/AKShare/CCXT/OpenBB APIs), and one AKShare "not installed" test skips because AKShare *is* installed here.
- Lint tools are available but the existing tree is **not** clean: `ruff check`, `black --check`, and `mypy src/openstrategy` all run but report pre-existing style/type findings (e.g. missing pandas stubs, unformatted test files). Do not treat these as regressions introduced by your change — compare against baseline.
- CLI: `openstrategy report [--output FILE]` generates the 6-question acceptance report on synthetic data. Other subcommands: `backtest -c <config>`, `optimize -c <config>`, `fetch --symbol ... --source ...` (fetch needs network).
- WebUI: `streamlit run src/openstrategy/ui.py --server.port 8501 --server.headless true`. Four offline pages (Home / Overfit Check / vs Buy & Hold / vs SPY). Run it as a long-lived process (e.g. a tmux-backed terminal), not in `install`.
- Runnable demos live in `examples/` (e.g. `python examples/comparison_demo.py`); a few `examples/*real*`/`*openbb*` scripts require network.
