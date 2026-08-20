# alphastrategy session clock and name rails

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-session-name-rails-technical-design.md`](../plans/2026-08-20-alphastrategy-session-name-rails-technical-design.md)

Paper only. Five screens. Quiet cockpit tokens unchanged. No sixth nav tab. No live. No WebSockets. Supervisor math unchanged.

This cycle makes **when the desk will trade** and **how close names are to the single-name cap** glanceable on Portfolio — the two questions a personal investor actually asks after first-run.

## 1. Why this increment exists

Goal check:

| Goal slice | Current desk |
| --- | --- |
| Stable execution | RTH countdown is a muted `#clock-line` footnote. v1 §8 lists countdown on Portfolio home; it does not look like home. |
| Risk controllable | Engine flattens if a name exceeds `max_name_weight` (default 20%). Gross has a util bar. Names do not. |
| Portfolio construction | `Σ allocation_i ≤ 1` is enforced, but the sleeves table never shows how much of the paper book is spoken for vs residual cash. |
| Reliable | `renderBanners` declares `const reason` twice in one function. Strict-mode JS throws when banners render; pytest does not execute the cockpit. |

Research (applied, not copied):

- **Countdown vs progress (UX.SE):** a countdown is the right control when the *event time* is the thing to plan around (next legal rebalance), not a completion fraction.
- **TradeX / execution desks:** concentration vs single-name cap must be visible on the book, not only in a Risk form. Surface the rail on the position row.
- **Quiet cockpit:** keep tokens and tabular numbers. Make session and countdown **metric tiles**, not a new screen.

## 2. Session and next rebalance tiles

Add two Portfolio metric cards (same `.metrics` grid):

1. **Session** (`#metric-session`): `OPEN` (running `#10b981`) or `CLOSED` (muted). Clock error: `UNAVAILABLE` (muted).
2. **Next rebalance** (`#metric-countdown`): `fmtCountdown(seconds)` as the value. `#metric-countdown-kind` shows `open` or `close`. Missing countdown: `—`.

Keep `#clock-line` for `now {timestamp}` only (no duplicated OPEN/CLOSED/countdown sentence).

## 3. Name cap rail

Positions table adds **Cap** after Book. CSS util-track: fill = `got / max_name_weight` (account cap, default 0.20). Same 90% warn / 100% fail tokens as Gross. `aria-label` includes got and cap percentages. Empty-row colspan becomes 7.

This does **not** change flatten math.

## 4. Sleeve allocation book

Under Sleeves `h2`, `#sleeve-alloc-track` fill = `sum(sleeve allocations) / 1`. Label `#sleeve-alloc-label`: `Spoken {pct} of paper book`. Hidden when there are no sleeve ids.

## 5. Banner JS

Rename the kill-outcome local to `killReason` so `renderBanners` has a single `const reason` (halt). Desk must not throw.

## 6. Focus-visible

`nav button`, `.action`, `#help-toggle`: `:focus-visible` outline `#9ba3b4`, 2px, offset 2px. Keyboard users who just shipped Alt+1–5 need a visible focus ring.

## 7. Help / README

One sentence: Session and Next rebalance are Portfolio tiles; Cap is name weight vs the account single-name limit; Sleeves show spoken share of the paper book.

## 8. In / out

**In:** session/countdown tiles; Cap rail; sleeve allocation track; banner `killReason`; focus-visible; help/README; tests.

**Out:** sixth screen; chart libraries; live; changing `max_name_weight` math; cloning Risk forms.

## 9. Verification

- HTML ids: `metric-session`, `metric-countdown`, `metric-countdown-kind`, `sleeve-alloc-track`, `Cap` column.
- JS: `renderSessionMetrics`, `nameCapBar`, `renderSleeveAllocBook`, `killReason`. `function renderBanners` block contains `const reason` once.
- CSS: `:focus-visible`, name/sleeve tracks reuse locked tokens.
- `#nav` still five screens. GET `/` includes `metric-countdown`.
- No real broker orders.
