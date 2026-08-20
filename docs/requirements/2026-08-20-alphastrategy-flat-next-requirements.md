# alphastrategy Clock Next is flat while the paper account is flattened

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §6–§8
**Related:** [`2026-08-20-alphastrategy-halt-next-held-requirements.md`](2026-08-20-alphastrategy-halt-next-held-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-flat-next-technical-design.md`](../plans/2026-08-20-alphastrategy-flat-next-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Start paper after flatten starts the session loop again. Keep tutorial substring `Next rebalance`. Halted Next stays `held ·` / warn.

The halt-next-held cycle marked Clock Next **held** while Supervisor is HALTED. A flattened book already shows a fail-red FLAT banner, but Next still ticks `open`/`close` in default color. Flattening and STOPPED ticks return before `_rebalance`. Start paper after flatten is the second explicit action that restarts the loop. Ticking Next on a FLAT desk fights 凭直觉: the loudest kill-switch rung sits next to a hero that still looks like the next fire.

## 1. Why this increment exists

Goal check against current main (`244bad7`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 稳定执行 | Flattening / STOPPED ticks do not rebalance. Start paper after flatten starts the session loop again and does not catch up. | Clock Next still counts down as if the next window will trade. |
| 凭直觉交互 | Flatten cannot look idle. Halt Next is already held. | FLAT banner is fail-red; Next hero is still a live auction clock. |
| 风险可控 | Account kill is the loudest rung. | Clock does not join that rung. |
| 易于使用 | Help: Start paper after flatten starts the session loop again. | Does not say Clock Next is flat while the paper account is flattened. |
| 界面令人眼前一亮 | Kill/fail `#ef4444` on FLAT banner and Supervisor FLATTENING/STOPPED. | Next does not use fail. |

Research applied:

- **Same inhibit pattern as halt.** Keep seconds (time-to-window). Flag the hero. Flatten uses **fail**, not halt/warn — flatten is not halt.
- **Do not merge Next into the flatten banner.** Banner stays the account story. Next stays the Clock hero.
- **API countdown stays a clock fact.** Paint is the honesty layer.

Stale `imported/.staging.*` after a crash between publish and rmtree is a separate architecture increment. Halted `held ·` stays.

## 2. Paint

In `renderSessionMetrics` countdown fork, after removing leftover classes:

| Condition (first match) | `#metric-countdown` | class | `#metric-countdown-kind` |
| --- | --- | --- | --- |
| countdown present, halted | `fmtCountdown(seconds)` | `warn` | `held · ` + kind (today) |
| countdown present, flattened (`status.flattened` or `state` is `flattening` / `stopped`) | `fmtCountdown(seconds)` | `fail` (not `warn`) | `flat · ` + kind |
| countdown present, else | `fmtCountdown(seconds)` | neither | kind (today) |

Always `countEl.classList.remove("warn", "fail")` before the fork. Halt wins over flat if both were ever true. Last spent `warn` stays on `#metric-last-rebalance` only.

No HTML mount change. No countdown JSON change.

## 3. Tokens

```css
#metric-countdown.fail {
  color: #ef4444;
}
```

Keep `#metric-countdown.warn` at `#f59e0b`. No new colors.

## 4. Help / README

`how_portfolio`: Clock Next is flat while the paper account is flattened.

README Clock: Next is flat while the paper account is flattened. Keep held-while-HALTED.

## 5. In / out

**In:** Next `flat ·` sub + fail class while flattened/flattening/stopped; CSS; help/README; tests.

**Out:** changing flatten recovery; resume catch-up; leftover `.staging.*` sweep; live; sixth screen; `app.js`; changing `countdown` JSON; changing halted `held ·`.

## 6. Verification

- `renderSessionMetrics` contains `flat · ` and `countEl.classList.add("fail")` when flattened. Keep `held · ` and countdown warn for halt.
- CSS `#metric-countdown.fail` is `#ef4444`. `#metric-countdown.warn` stays `#f59e0b`.
- Help contains `Clock Next is flat while the paper account is flattened` and still contains `Next rebalance` and `Clock Next is held while Supervisor is HALTED`.
- Five `#nav` screens. `"Gross cap"` not in `js_text`. No real broker.
