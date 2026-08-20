# alphastrategy operator help and architecture explanation

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-operator-help-technical-design.md`](../plans/2026-08-20-alphastrategy-operator-help-technical-design.md)

This document does **not** change product identity. alphastrategy remains a local Alpaca **paper** execution desk. alphaloop still searches; this product still runs qualified `.asb` bundles. Live money, crypto, WebSockets, a strategy editor, VWAP/TWAP, public bind, a sixth nav screen, and in-app search stay out of scope.

It closes a documentation and operator-surface gap: the Supervisor already implements halt ≠ flatten, isolated sleeve kill, and wanted vs got; an operator at the desk or at `alphastrategy --help` still cannot recover those meanings without reading source.

## 1. Why this increment exists

Gap pass against v1 §5 (runtime architecture), §7 (halt vs flatten), §8 (Quiet cockpit), §9 (CLI), README, `AGENTS.md`, and CLI argparse copy:

| Need | Current behavior |
| --- | --- |
| Nielsen heuristic 10: help is task-focused, in context, lists concrete steps | Operator copy lives only in README. The cockpit has five screens and no Help control. `alphastrategy --help` is a generic argparse listing. |
| Diátaxis: explanation vs how-to vs reference | `docs/` is requirements + plans + lessons with no index. README “Architecture” is a **directory tree**, not a system-context / container map. |
| C4 (context + container) for a small single-process desk | v1 §5 ASCII (Web/CLI → control plane → Supervisor → sleeves) is the contract, but it is not the first diagram an operator or agent sees. |
| CLI reference matches v1 verbs | `paper kill` help is “kill sleeve or account”. It does not say **flatten**. Resume help does not say **no catch-up**. Empty argv prints argparse help with no halt/flatten warning. |
| Agent / contributor help | `AGENTS.md` still describes the openstrategy Streamlit research library (`openstrategy report`, `streamlit run`). That is the wrong product. |

Execution and UX research (applied, not copied):

- **Nielsen / Molich heuristic 10** (Help and Documentation): help must be easy to find, focused on the user’s task, list concrete steps, and stay short. Do not ship a searchable knowledge base or adaptive pop-ups.
- **NN/g on overlays:** a small non-modal panel beats a modal that hides the work. Advanced detail lives in `docs/`.
- **Stocktrader workstation (Burmistrov, HCII 2003):** trading UIs must not cover alerts with overlapping dialogs. Help is an **aside**, never a modal over `#halt-banner` / `#flatten-banner`.
- **Diátaxis:** argparse `--help` is **reference**. `alphastrategy help` and the cockpit panel are a **how-to** runbook. `docs/explanation/architecture.md` is **explanation** (why one Supervisor, why paper-only).
- **C4 (Simon Brown):** for this single-process product, document **context** and **containers** only. Skip a class diagram.
- **Kill-switch ladder** (HFT Book; operator runbooks): halt (block new orders, hold the book) and flatten (trade to flat) are different rungs. The desk already implements that. Help must teach it in the same words as v1 §7.

## 2. Positioning walls (unchanged)

All v1 hard walls remain:

1. Alpaca paper only. No live control in CLI or Web.
2. No credentials in `.asb`, logs, UI, or help copy.
3. Interpreters never see secrets, network, or the broker.
4. Import is not permission to trade.
5. Supervisor is the only order placer. Heartbeat still does not place orders.
6. Resume still does not catch-up rebalance.
7. Quiet cockpit tokens stay locked. **Five screens stay five.** Help is not a sixth nav tab.

## 3. Canonical operator copy (one source)

Ship a Python module `alphastrategy.helptext` that is the single source of operator how-to copy. CLI, `GET /api/help`, and the cockpit panel consume it. Do not duplicate paragraphs in `app.js`.

The payload is JSON-serializable:

```text
{
  "title": "alphastrategy operator help",
  "sections": [
    {"id": "<slug>", "title": "<heading>", "body": "<plain text>"}
  ]
}
```

Required section ids, in order:

| id | Answers |
| --- | --- |
| `identity` | This is a paper execution desk. alphaloop searches; this product runs `.asb`. Import is not permission to trade. |
| `execution` | Supervisor is the sole order placer. Heartbeat every 20s does not order. At most two RTH rebalances (open +3 min, close −12 min). Combined target = Σ allocation × sleeve weights. Residual is cash. |
| `halt_flatten` | Halt is not flatten. Halt: no new orders, hold positions. Flatten: cancel open orders and trade the paper account (or isolated sleeve) to the residual/flat book. Stop waits for the next rebalance. Resume does not catch up. Account kill on the Web requires typing `FLATTEN`. |
| `cockpit` | Five screens: Portfolio, Strategies, Run, Activity, Risk. Wanted is last combined target; Got is current weight. FLAT banner means the paper account was flattened. |
| `cli` | The v1 verbs: `start`, `import`, `paper start`, `paper stop`, `paper kill`, `paper resume`, `status`. `paper kill` without `--bundle` flattens the whole account. |
| `walls` | Paper only. Loopback control plane. No live toggle. No secrets in the UI. |

Plain-text rendering (`help_text()`) is the same sections as titled paragraphs, suitable for a terminal. It **must** contain these phrases (case-insensitive match is enough in tests):

- `halt is not flatten`
- `paper only`
- `sole order placer` (or `only order placer`)
- `does not catch up`
- `FLATTEN`
- `Wanted`
- `Got`

Help copy must not mention live trading as an available action, must not mention Streamlit, and must not mention `openstrategy` as the product to run.

## 4. CLI reference and how-to

1. `alphastrategy help` prints `help_text()` to stdout and exits 0. It does not start the control plane or construct Alpaca.
2. `alphastrategy --help` remains argparse **reference**: command list plus a short epilog that says halt is not flatten, paper only, and points to `alphastrategy help`.
3. Subcommand help strings, verbatim intent:
   - `paper kill`: flatten one sleeve, or the whole paper account if `--bundle` is omitted. This is not halt.
   - `paper resume`: resume from halt; does not catch up; does not flatten.
   - `paper stop`: zero that sleeve on the next legal rebalance; does not flatten now.
   - `start`: localhost Quiet cockpit + Supervisor; paper only.
4. v1 CLI still rejects live flag combinations. Help must not advertise them.

## 5. Control-plane API

`GET /api/help` returns HTTP 200 and `help_payload()` JSON (`Content-Type: application/json`). No auth. No secrets. No broker call. The route exists even if the supervisor is halted or flattened.

## 6. Quiet cockpit presentation

Keep the five `#nav` screens exactly: Portfolio, Strategies, Run, Activity, Risk.

Add a **Help** control **outside** `#nav`:

- Element `#help-toggle` (button). `aria-expanded` reflects open/closed. `aria-controls="help-panel"`.
- Element `#help-panel` (`<aside>`), `aria-label="Operator help"`. Closed by default (`hidden` class or equivalent). Not a `.screen` and not a `data-screen`.
- Opening Help does **not** call the screen switcher and does **not** hide `#halt-banner`, `#flatten-banner`, `#deviation-banner`, or `#control-plane-banner`.
- The panel is a right-hand aside in the existing night palette (surface `#11151d`, border `#2a3142`, text `#e5e9f0`). It is not a full-viewport modal.
- On open, fetch `GET /api/help` once and render `sections` as headings + body text. If the fetch fails, show a readable error inside the panel; do not `console.error` only.
- Escape closes the panel. Toggle closes it.

Do not add tooltips on every column, onboarding carousels, or a Help nav tab.

## 7. Explanation documents (not the cockpit)

Diátaxis explanation lives in git, not in the trading chrome.

1. `docs/index.md` — map of docs: how-to (README + in-desk Help), reference (`docs/requirements/`, CLI), explanation (`docs/explanation/`), plans (`docs/plans/`), lessons (`docs/lessons/`). Link the v1 contract first.
2. `docs/explanation/architecture.md` — **About the alphastrategy runtime**. C4 context (operator, alphastrategy, alphaloop as export-only, Alpaca paper) and C4 container (CLI, Quiet cockpit static files, localhost control plane, Supervisor, sleeve sandboxes, home directory, Alpaca paper API). State explicitly: alphaloop is not a runtime dependency; there is no telemetry back. One Supervisor, one paper account. ASCII or Mermaid; no UML class dump.
3. README **Architecture** section shows the v1 §5 runtime diagram (not only a folder tree) and links `docs/index.md` and `docs/explanation/architecture.md`.
4. `AGENTS.md` describes **this** product: package `alphastrategy`, tests `PYTHONPATH=src python3 -m pytest tests/alphastrategy/`, cockpit at `127.0.0.1:7460`, paper only, do not grow `src/openstrategy/`. Historical `src/openstrategy/` may be mentioned as unpackaged history, not as the thing to run.

## 8. v1 in / out for this increment

**In**

- Canonical `helptext` module
- `alphastrategy help` + argparse epilog + precise kill/resume/stop help
- `GET /api/help`
- Non-modal Help aside in the Quiet cockpit
- `docs/index.md`, `docs/explanation/architecture.md`, README architecture, `AGENTS.md` identity cut

**Out**

- Sixth nav screen named Help
- Modal overlay, guided tour, search, i18n, chat assistant
- Changing halt/flatten/kill **behavior**
- Per-sleeve allocation editor on Run (still a later v1 §8 polish)
- Sleeve-kill `FLATTEN` confirm (account kill already requires it)
- Live money, public bind, WebSockets

## 9. Verification

- Unit: `help_payload()` section ids and required phrases; `help_text()` is non-empty and has no `openstrategy` product instructions.
- CLI: `alphastrategy help` exits 0 and prints the phrases; `--help` epilog mentions halt is not flatten; `paper kill --help` mentions flatten; live flags still rejected.
- API: `GET /api/help` 200 JSON with the same section ids; no credential fields.
- Web: HTML has `#help-toggle` and `#help-panel`; `#nav` still has exactly the five screens; Help is not `data-screen="help"`; JS fetches `/api/help` and toggles `aria-expanded`; CSS aside uses locked tokens.
- E2E (mocked broker): control plane serves `/api/help` and `/` including the Help control.
- Packaging/docs: README links `docs/index.md`; `AGENTS.md` contains `alphastrategy` and `tests/alphastrategy` and does not instruct `streamlit run` as the product UI.
- No test places a real order.
