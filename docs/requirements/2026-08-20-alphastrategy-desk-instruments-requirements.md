# alphastrategy Book takes LIMIT color; header chips are instruments

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §8
**Related:** [`2026-08-20-alphastrategy-header-chips-requirements.md`](2026-08-20-alphastrategy-header-chips-requirements.md), [`2026-08-20-alphastrategy-limit-send-requirements.md`](2026-08-20-alphastrategy-limit-send-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-desk-instruments-technical-design.md`](../plans/2026-08-20-alphastrategy-desk-instruments-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. GET must not flatten. Keep `Next rebalance`. Keep Caps **four tiles** and `#risk-cap-order`. Keep LIMIT book vs send copy. Do **not** overwrite Cash composition subs. Each JS part stays ≤ 400 lines. Do not hardcode `Order size` in JS.

v1 §8: halt/deviation banners cannot be visually quiet; Portfolio home is equity, cash, day PnL, gross, clock. After LIMIT book/send copy, the banner names the check, but Book Equity / Cash / Day PnL / Drift still look like a calm form. Header Pulse / Session / Supervisor are 0.72rem captions in the brand line. That is not 界面令人眼前一亮 or 凭直觉交互.

## 1. Why this increment exists

Goal check against current main (`a34c541`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 界面令人眼前一亮 | Instrument cluster: chrome status + one hero number. Locked tokens. | Header chips are muted captions. Hero is 1.85rem on the same card chrome as Drift. |
| 凭直觉交互 | Alarming modules take warn/fail color (Nielsen visibility; Bloomberg module rails). | LIMIT is a banner only. Book glance stays the default borderless stack. |
| 风险可控 | A next rebalance that will flatten cannot look healthy on home. | Clock Next flatten exists; Book Equity does not change. |
| 易于使用 | Help: Book takes LIMIT color; header chips are instruments. | Help names Pulse / Session / Supervisor, not that they are instruments. |

Research applied:

- **Operator chrome is instruments, not labels.** Pulse / Session / Supervisor sit in header on every screen. Give them the same surface language as `.metric` (border `#2a3142`, fill `#0b0e14`). LIVE / STALE / DEAD / OPEN / HALTED / FLAT already paint text color; add matching **border-color**.
- **Book rail is reserved, then colored.** Always a 2px left rail (transparent until it matters) so LIMIT/flatten does not reflow. Warn `#f59e0b` when `live_limit.reason` and not flattened. Fail `#ef4444` when flattened / flattening / stopped.
- **Hero scale.** `.metric.hero .metric-value` 2.35rem (was 1.85rem). Equity stays the Book hero. No new color. No chart.

Out: fifth Caps tile; GET flatten; live; sixth screen; box-shadow colors other than locked tokens; painting Beat/Glance onto Cash composition subs.

## 2. Header instruments

Keep ids `#desk-pulse`, `#desk-session`, `#desk-supervisor`. No HTML change required.

CSS:

- `.desk-pulse` and `.desk-chip`: `border: 1px solid #2a3142`, `background: #0b0e14`, `border-radius: 4px`, padding, keep tabular feel.
- `.desk-pulse.live` border-color `#10b981` (keep text `#10b981`).
- `.desk-pulse.stale` and `#desk-session.warn` border-color `#f59e0b`.
- `.desk-pulse.dead` and `#desk-supervisor.fail` border-color `#ef4444`.
- `#desk-supervisor.halt` border-color `#f59e0b`.
- Keep `@media (prefers-reduced-motion: reduce)` disabling the LIVE opacity animation.

Do not add a header LIMIT chip (the banner is already global).

## 3. Book LIMIT rail + hero

`#glance-book` always has `border-left: 2px solid transparent` and matching left padding.

`paintBookLimitRail()` in `paint-rails.js` (portfolio is already near 400 lines):

1. Remove `warn` / `fail`.
2. If flattened (`status.flattened` or state `stopped` / `flattening`) → `fail`.
3. Else if `utilization().live_limit.reason` → `warn`.

`renderPortfolio` calls `paintBookLimitRail()`. Do not put `Gross cap` or `Order size` in JS.

`.metric.hero .metric-value { font-size: 2.35rem; }`

## 4. Help / README

Phrases (exact):

- `Book takes LIMIT color while a next rebalance will flatten`
- `Header Pulse, Session, and Supervisor are instruments`

Add to `cockpit`, `how_portfolio`, `halt_flatten`, README Operator. Keep `Header shows Pulse, Session, and Supervisor`. Keep `Next rebalance`. Keep LIMIT send/book sentences.

## 5. In / out

**In:** header instrument chrome; Book LIMIT rail; hero 2.35rem; help/README; CSS/JS/help tests.

**Out:** GET flatten; fifth Caps tile; header LIMIT chip; new tokens; live; sixth nav.

**Done when:**

1. CSS: `.desk-pulse.live` border `#10b981`; `#glance-book.warn` `#f59e0b`; `#glance-book.fail` `#ef4444`; hero `2.35rem`.
2. JS `paintBookLimitRail` toggles `#glance-book` warn/fail from live_limit / flattened; `renderPortfolio` calls it.
3. Help contains both phrases. Five `#nav` screens. `"Gross cap"` not in assembled JS. No real broker.
