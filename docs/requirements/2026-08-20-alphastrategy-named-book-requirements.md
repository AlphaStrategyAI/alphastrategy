# alphastrategy names the working blotter on Book, Beat, Headroom, and status

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md) §5–§9
**Related:** [`2026-08-20-alphastrategy-runtime-book-requirements.md`](2026-08-20-alphastrategy-runtime-book-requirements.md), [`2026-08-20-alphastrategy-sticky-book-requirements.md`](2026-08-20-alphastrategy-sticky-book-requirements.md), [`2026-08-20-alphastrategy-caps-limit-requirements.md`](2026-08-20-alphastrategy-caps-limit-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-named-book-technical-design.md`](../plans/2026-08-20-alphastrategy-named-book-technical-design.md)

Paper only. Five screens. Quiet cockpit **tokens unchanged**. No sixth nav tab. No live. No WebSockets. No chart library. Do not revive `static/app.js`. `"Gross cap"` must not appear in assembled JS. `renderBanners` keeps a **single** `const reason`. Do not retry leftover orders. Resume does not catch up. Heartbeat still does **not** flatten. Keep `Next rebalance`. Keep sticky heartbeat live book, runtime/envelope digest, Equity subcopy, LIMIT stderr. Idle overlays stay unpublished. GET `/api/status` and `/api/risk` must not flatten. Do not feed order sizing from the glance cache. Each JS part stays ≤ 400 lines. CLI stdout stays one JSON object.

v1 §8: Portfolio Book, Activity, and Risk Headroom all read the same working blotter. v1 §9: `status` is the secondary surface. Equity now names Beat or Glance; the Book heading, Activity Beat heading, Headroom heading, and CLI `status` still look unlabeled. Offline `status` JSON omits `book` entirely. An operator who never looks at the Equity subcopy still thinks NAV is a live stream. That is not 凭直觉交互 or 界面令人眼前一亮.

## 1. Why this increment exists

Goal check against current main (`b667ac7`):

| Goal slice | v1 / later contract | Current desk |
| --- | --- | --- |
| 凭直觉交互 | Every panel that uses `live_book()` names Beat or Glance. | Only Equity subcopy. Cash / Headroom / Beat pulse look live. |
| 界面 | Band headings carry the snapshot label in muted type. | Headings are static `Book` / `Beat` / `Headroom`. |
| 易于使用 | CLI `status` names BOOK on stderr like LIMIT. | LIMIT only. Offline JSON has no `book`. |
| 可靠 | Kill still drops sticky; headings follow `book.source`. | Engine already correct; paint/CLI lag. |
| 风险可控 | LIMIT stderr still fires. BOOK does not replace it. | Unchanged if we add a second stderr line. |

Research applied:

- **Name the blotter on every panel that consumes it.** OMS desks stamp “snapshot / poll” on NAV, cash headroom, and the heartbeat strip — not only the hero number.
- **CLI stderr is the spoken line; stdout stays machine JSON.** Same pattern as `LIMIT:`. Words `heartbeat` / `glance` match `book.source`. Omit BOOK when source is `none` (offline status that did not glance).
- **Do not overwrite Cash / Headroom cash composition subs.** Those already mean invested vs residual. Put the source on the band heading.
- **Do not add a sixth tile or a Live trading mode.**

Out: heartbeat flatten; GET flatten; JS charts; live; `app.js`; changing Caps/Clock paint; making offline status hit the broker (`live=False` stays).

## 2. Engine / API / paint / CLI

`live_book_source()` unchanged. Online GET status already has `book`.

Offline `_cmd_status` payload includes `"book": {"source": supervisor.live_book_source()}` (typically `"none"`). Do not switch utilization to `live=True`.

`_print_status`: after JSON, if `book.source` is `heartbeat` or `glance`, stderr `BOOK: heartbeat` or `BOOK: glance`. Then the existing LIMIT line if any.

HTML: Book / Beat / Headroom headings gain `#book-source`, `#act-book-source`, `#risk-book-source` (class `glance-source`). `paintBookSourceHeadings()` in `paint-rails.js` writes `bookSourceLabel()` into those spans (empty when `—`). Call from `renderDeskPulse` so one refresh paints all three.

CSS: `.glance-source` uses `#5c6573`. Keep heading uppercase.

## 3. Help / README

- `Book, Beat, and Headroom name Beat or Glance`
- `status names BOOK heartbeat or glance`

Keep Equity and LIMIT sentences. `"Gross cap"` in help labels only.

## 4. In / out

**In:** heading sources; CLI BOOK stderr; offline JSON `book`; help/README; tests.

**Out:** heartbeat flatten; GET flatten; offline broker glance; JS; live; `app.js`.

**Done when:**

1. HTML Book / Beat / Headroom headings contain the three source ids. Assembled JS has `paintBookSourceHeadings` and no `"Gross cap"`.
2. Offline `status` JSON includes `book.source`. Control-plane `status` with `book.source=heartbeat` prints `BOOK: heartbeat` on stderr; stdout remains one JSON object.
3. LIMIT stderr still prints when the live book is through a spoken cap.
4. Help contains both new phrases. Five `#nav` screens. No real broker.
