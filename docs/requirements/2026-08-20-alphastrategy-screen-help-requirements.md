# alphastrategy screen-aware operator help

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-screen-help-technical-design.md`](../plans/2026-08-20-alphastrategy-screen-help-technical-design.md)

Paper only. Five screens. Quiet cockpit tokens unchanged. Help stays an **aside**, never a sixth `#nav` tab. No live. No in-app search. Canonical runbook sections stay the six ids already shipped.

This cycle makes F1 **task-shaped**: the aside answers the current screen first; the full runbook is one click behind.

## 1. Why this increment exists

Goal check against current main (`b6bf86c`):

| Goal slice | Contract / research | Current desk |
| --- | --- | --- |
| 易于使用 | Nielsen heuristic 10: help is task-focused, short, in context | F1 dumps identity → walls regardless of whether the operator is on Portfolio or Run. |
| 凭直觉交互 | Diátaxis **how-to** vs reference; NN/g contextual help | One blob. Portfolio glance bands and spoken Risk labels are documented inside the Quiet cockpit essay, not next to those screens. |
| 帮助文档 | Operator-help cycle: argparse is reference; `alphastrategy help` + aside are how-to | The aside is the same six essays as the CLI. No per-screen how-to. |
| 风险可控 / 组合 | Halt ≠ flatten, flatten budgets, Gross cap | Those meanings exist, but not at the point of use on Run / Risk / Portfolio. |
| 架构 | `helptext.py` is the single source | Do not copy paragraphs into `app.js`. Ship how-tos from the same module. |
| 眼前一亮 | Sparse chrome | A wall of h3 essays in the aside is chrome. A short “On Portfolio” plus `<details>Full runbook</details>` is quieter. |

Research applied:

- **Nielsen / Molich 10** and **NN/g contextual help:** show the task for this screen; keep the encyclopedia available, not first.
- **Diátaxis:** screen how-tos are how-to. The six existing sections remain the runbook. argparse `--help` stays reference.
- **Stocktrader workstation:** Help stays a non-modal aside. It must not cover `#halt-banner`.

## 2. Screen how-tos (Python source of truth)

Add `SCREEN_HOWTOS` in `alphastrategy.helptext`, five entries, `id` / `screen` / `title` / `body`. Screens are exactly the five nav ids.

| screen | id | title | Answers |
| --- | --- | --- | --- |
| portfolio | `how_portfolio` | On Portfolio | Three bands Book / Flatten budgets / Clock; Equity hero; Positions Book column; LIVE ≠ Session. |
| strategies | `how_strategies` | On Strategies | Import `.asb`; import is not permission to trade; failures name the gate; start paper on Run. |
| run | `how_run` | On Run | Start is the second action; Stop waits for the next rebalance; sleeve kill vs account `FLATTEN`; resume does not catch up. |
| activity | `how_activity` | On Activity | Audit blotter; empty copy names the two rebalances; kill rows isolated residual vs flattened account. |
| risk | `how_risk` | On Risk | Account caps always visible; desk words Gross cap / Names / Orders today; tighten only; posts policy keys. |

`help_payload()` grows `"howtos": [ ...copies... ]` and **keeps** `"sections"` as today. CLI `help_text()` prints each how-to (title + body) **before** the six runbook sections.

## 3. Quiet cockpit

Aside structure:

1. `#help-howto` — current screen’s how-to (title + body).
2. `#help-runbook` — `<details><summary>Full runbook</summary>` wrapping the existing `#help-body` essays.

`renderHelp` uses the active `#nav` button’s `data-screen`. `showScreen` re-paints Help when a payload is loaded so Alt+1–5 updates the aside without closing it.

No `window.confirm`. No sixth nav button.

## 4. Help / README

One sentence: F1 is how-to for the current screen; Full runbook is the same six sections as `alphastrategy help`.

## 5. In / out

**In:** five screen how-tos in `helptext`; payload `howtos`; CLI prints them first; cockpit `#help-howto` + details runbook; re-paint on screen change; tests.

**Out:** searchable help; sixth screen; rewriting the six runbook essays into a wiki; splitting `app.js`; live; new tokens.

## 6. Verification

- `SCREEN_HOWTOS` screens == `portfolio, strategies, run, activity, risk` in that order.
- `help_payload()["howtos"]` matches; `sections` ids unchanged.
- `help_text()` contains `On Portfolio` and still contains `halt is not flatten`.
- GET `/api/help` includes `howtos[0].id == how_portfolio`.
- HTML: `id="help-howto"`, `id="help-runbook"`, `Full runbook`; five nav screens; `data-screen="help"` absent.
- JS: `help-howto`, re-render from `showScreen`; no `window.confirm`.
- No real broker orders.
