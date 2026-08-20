# alphastrategy desk keyboard accelerators

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-desk-keys-technical-design.md`](../plans/2026-08-20-alphastrategy-desk-keys-technical-design.md)

Paper only. Five screens. Quiet cockpit tokens unchanged. No sixth nav tab. No `window.confirm`. No character-only shortcuts that fire while typing (WCAG 2.1.4).

## 1. Why this increment exists

Goal slice **intuitive interaction**: first-run chrome teaches the novice; the repeating job is still clicking `#nav`. Nielsen heuristic 7 (accelerators) plus NN/g: show the shortcut next to the command, unobtrusive.

WCAG 2.1.4 forbids unmodifiable **character-key** shortcuts (bare `1`–`5` or `?`) unless they can be turned off or only run when a widget has focus. This desk therefore uses **modifier chords and F1**, not bare digits.

Research (applied, not copied): accelerators must not steal from `<input>` / `<select>` / `<textarea>` unless they include a non-character modifier; expose them with a muted hint and `aria-keyshortcuts`.

## 2. Behavior

| Keys | Action |
| --- | --- |
| `Alt+1` … `Alt+5` | `showScreen` portfolio, strategies, run, activity, risk |
| `F1` | Toggle Help aside (same as `#help-toggle`) |
| `Escape` | Close Help (already) |

Ignore when `ctrlKey` or `metaKey` is set (browser tab chords). `preventDefault` on handled Alt+Digit and F1.

Visible hint in the header, not a nav tab: `Alt+1–5 · F1 help` (`#kbd-hint`).

Each `#nav` button gets `aria-keyshortcuts` (`Alt+1` … `Alt+5`). `#help-toggle` gets `aria-keyshortcuts="F1"`.

## 3. In / out

**In:** Alt+1–5, F1, header hint, aria-keyshortcuts, help/README one-liner.

**Out:** bare `1`–`5`, remapping UI, command palette, sixth screen, live.

## 4. Verification

- HTML: `#kbd-hint`, `aria-keyshortcuts="Alt+1"` … `Alt+5`, `F1` on help-toggle. `#nav` still five screens.
- JS: `Alt+`, `Digit1`, `F1`, `preventDefault`. No handler that maps bare `ev.key === "1"`.
- Help mentions `Alt+1`. No real broker orders.
