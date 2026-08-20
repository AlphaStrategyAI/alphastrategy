# alphastrategy desk first glance

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-desk-first-glance-technical-design.md`](../plans/2026-08-20-alphastrategy-desk-first-glance-technical-design.md)

This document does **not** change product identity. Paper only. Five screens. Help stays an aside. Locked Quiet cockpit tokens stay. No live toggle, no WebSockets, no demo positions that look like a live book.

It serves the product goal — a **personal investor** paper desk that is reliable, risk-visible, and usable on first open — without turning the Quiet cockpit into a research lab or a marketing illustration.

## 1. Why this increment exists

Goal check (reliable / risk-controlled / stable execution / easy / glanceable / intuitive):

| Goal slice | Current desk |
| --- | --- |
| Intuitive first open | Portfolio metrics are `—`. Positions say `No positions`. No next action. Import is two screens away. |
| Glanceable execution | Wanted and Got are two numbers. A personal investor cannot see miss-vs-target without subtracting. |
| Risk controllable | Gross is a percentage with no rail. Risk sleeve overlays do not show **allocation** (v1 §8). |
| Easy to maintain | Empty copy is one string for every cause of an empty book (never imported vs imported-not-started vs waiting on rebalance). |

Research (applied, not copied):

- **NN/g empty states:** tell the user what belongs here and give a direct path to populate it. Do not leave a configured-looking void.
- **Investment dashboard first-run (Lollypop / empty-state playbooks):** the empty dashboard is an activation surface. For a **trading desk**, do **not** inject ghost fills or demo positions — that would look like a paper book. Teach the two-step handoff instead: import, then start paper.
- **Target vs actual weights (Koyfin-class request, execution blotters):** a bar with target mark vs fill is how operators scan rebalance error. Keep the numbers (Quiet cockpit, tabular).
- **Risk utilization gauges (execution desks):** show used vs cap, not only the cap. Color with existing halt/fail tokens at 90% / 100%. The engine still enforces the cap; the bar only renders it.

## 2. Positioning walls (unchanged)

All v1 hard walls remain. Tokens remain `#0b0e14` / `#11151d` / `#2a3142` / `#e5e9f0` / `#5c6573` / `#9ba3b4` / `#10b981` / `#f59e0b` / `#ef4444`. No sixth `#nav` screen. No `window.confirm`. No live. Do not clone Run allocation **forms** onto Risk.

## 3. First-run chrome

A `#first-run` panel is a **sibling of `#desk-banners`** (inside `main`, outside every `.screen`) so it stays visible on Portfolio, Strategies, Run, Activity, and Risk.

Show it only when there are **no imported bundle ids** (`imported` list empty and `paper` object empty). Hide it as soon as any bundle is imported.

Locked copy:

- Heading: `Start this paper desk`
- Body: `Import a qualified .asb, then start a paper sleeve. Import is not permission to trade.`
- Primary button: `Import .asb` — `data-go-screen="strategies"`
- Secondary button: `Open Run` — `data-go-screen="run"`

`role="status"`. Green border using `--running` (`#10b981`). Not a halt/fail banner.

Clicking `data-go-screen` calls the existing `showScreen` (same as `#nav`). Do not add a sixth nav tab.

## 4. Empty positions (not first-run)

Positions table empty row (locked):

| Desk state | Copy |
| --- | --- |
| No imports | `No positions yet. Import a .asb to begin.` |
| Imports, no paper sleeve (allocation 0 / not in paper) | `Imported bundles are not trading. Start paper on Run.` |
| At least one paper sleeve, no positions | `No positions yet. The next legal open or close rebalance will trade.` |

Do not invent fills.

## 5. Wanted vs Got bar

Keep Wanted and Got numeric columns. Add a **Book** column with a CSS bar (no chart library):

- Track width represents `max(account max_name_weight, wanted, got, 0.01)`.
- Fill = Got (running green). Marker = Wanted (text color).
- If `|wanted − got| > 0.001`, add class `drift` and fill uses halt `#f59e0b`.
- `aria-label` includes both percentages.

## 6. Gross utilization

Under the Gross metric, a `.util-track` fill = `gross / account.max_gross` (default cap 1 if risk has not loaded).

| Fill / cap | Class |
| --- | --- |
| `< 0.9` | (running) |
| `≥ 0.9` and `< 1` | `warn` (halt token) |
| `≥ 1` | `fail` |

The numeric Gross percentage stays. The bar does not change Supervisor math.

## 7. Risk sleeve allocation (read-only)

Each Risk sleeve overlay heading includes `Allocation {pct}` from `bundles.paper[id]` (0 if absent). Text only. No allocation input on Risk.

## 8. Help / README

One sentence each: empty desk tells you to import then start paper; Portfolio Book column is wanted vs got; Gross utilization is against the account cap; Risk lists sleeve allocation as text.

## 9. In / out

**In:** `#first-run`; three empty-position strings; Book bar; Gross util track; Risk allocation text; help/README; tests on static HTML/JS/CSS and GET `/`.

**Out:** demo/ghost positions; chart libraries; WebSockets; sixth screen; cloning Run forms onto Risk; live; changing isolation math or kill confirm.

## 10. Verification

- HTML has `#first-run`, Book column, `data-go-screen`.
- JS has `renderFirstRun` / `wantedGotBar` / `util-track` / `data-go-screen` / the three empty-position phrases.
- CSS has `.wg-track`, `.util-track`, `.first-run` using only locked tokens.
- `#nav` still exactly five screens. `window.confirm` still absent.
- GET `/` includes `#first-run`.
- No real broker orders.
