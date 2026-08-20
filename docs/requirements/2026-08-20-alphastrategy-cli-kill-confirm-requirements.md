# alphastrategy CLI account-kill confirmation

**Date:** 2026-08-20
**Status:** Requirements (improvement cycle on v1)
**Repo:** `AlphaStrategyAI/alphastrategy`
**Parent contract:** [`2026-08-19-alphastrategy-v1-requirements.md`](2026-08-19-alphastrategy-v1-requirements.md)
**Technical design:** [`docs/plans/2026-08-20-alphastrategy-cli-kill-confirm-technical-design.md`](../plans/2026-08-20-alphastrategy-cli-kill-confirm-technical-design.md)

This document does **not** change product identity. Paper only. Isolation math, Web `FLATTEN` confirm, sleeve-kill checkbox, and `KillOutcome` JSON stay as they are. This cycle closes the remaining loudness gap: **CLI account kill is as loud as Web account kill, and fail-closed when nobody can answer a prompt.**

It **supersedes** the kill-outcome contract sentence that CLI `paper kill` “does not add an interactive confirm.” That sentence remains true for **sleeve** kill (`--bundle`). It is **false** for **account** kill (omit `--bundle`).

## 1. Why this increment exists

Gap pass against v1 §7–§9, operator-desk loudness, Quiet cockpit Help, README, and `alphastrategy paper kill --help`:

| Need | Current behavior |
| --- | --- |
| v1 §8 / operator-desk: account kill is **louder** than sleeve kill | Web requires checkbox + typed `FLATTEN`. CLI `paper kill` (no `--bundle`) flattens immediately. |
| Nielsen heuristic 5: prevent irreversible mistakes | Sleeve CLI kill has no confirm (Web has a checkbox). Account CLI kill has **no** gate at all. |
| Unattended / non-TTY safety | pytest, CI, pipes, and agents are not TTYs. A prompt would hang; skipping the prompt would flatten silently. |

Research (applied, not copied):

- **Nielsen heuristic 5 (Error prevention):** present a constraint before a high-cost flatten. Typed-name confirm is the existing desk ritual (`FLATTEN`), matching GitHub-style “type the name” for large blast radius. Do not invent a second phrase.
- **Kill-switch literature:** flatten is a human decision. The Web already treats account flatten that way. The CLI is the same verb against the same Supervisor.
- **Modern CLI destructive-op practice** (heygen-cli #72, tene I-12, ironflow `confirm.rs`, similar fail-closed CLIs): if stdin is not a TTY, **refuse** unless an explicit bypass flag is set. Do **not** treat missing TTY as implicit yes (that is a known data-loss class: `echo n \| delete` still deleted). Do **not** treat piped `FLATTEN` on a non-TTY as confirmation either — that would re-open the pipe-as-yes hole. Prefer **`--force`** for destructive bypass; **`--yes`** stays out (it is for benign prompts).
- **Prompts on stderr:** JSON kill outcome stays on stdout so scripts that pass `--force` keep a machine-readable channel.

## 2. Positioning walls (unchanged)

All v1 hard walls remain. Five screens remain. Help remains an aside. `kill_sleeve` isolation rules, halt ≠ flatten, Web account `FLATTEN`, and sleeve-kill checkbox stay as they are. No live, no WebSockets, no `window.confirm`, no sixth nav screen, no cloning Risk onto Run.

HTTP `POST /api/paper/kill` stays unprompted: the Quiet cockpit already confirms before that POST. This cycle gates the **CLI verb**, not the control plane.

## 3. CLI account kill (omit `--bundle`)

`alphastrategy paper kill` with **no** `--bundle` is account flatten. Before any HTTP POST or offline `kill_account`:

| Condition | Behavior |
| --- | --- |
| `--force` | Skip the prompt. Then kill. Print `KillOutcome` JSON on stdout as today. |
| stdin is **not** a TTY, and no `--force` | Do **not** kill. Exit **1**. Stderr exactly: `error: account kill requires confirmation; pass --force` |
| stdin **is** a TTY, and no `--force` | Prompt on **stderr**: `Type FLATTEN to flatten the whole paper account:` Read one line from stdin. Proceed only when that line with trailing CR/LF removed equals `FLATTEN` (case-sensitive, no other trimming — same as the Web input). Otherwise do **not** kill, exit **1**, stderr exactly: `error: type FLATTEN to flatten the whole paper account` |
| EOF / empty line on a TTY | Same as wrong phrase: refuse, exit 1, same wrong-phrase stderr. |

`--force` on a **sleeve** kill (`--bundle` present) is accepted and ignored. Sleeve kill does **not** prompt and does **not** require `--force`.

Piped stdin (`echo FLATTEN | alphastrategy paper kill`) is **not** a TTY: refuse unless `--force`. Operators who need unattended flatten pass `--force` explicitly.

## 4. What does not change

- SIGINT/SIGTERM on `alphastrategy start` still calls `_shutdown_flatten` with no `--force` (the process is already dying).
- Limit-breach flatten inside the Supervisor is unchanged.
- `KillOutcome` JSON shape and `last_kill` banners are unchanged.
- Web account kill still uses checkbox + `FLATTEN`; it does not grow a `--force` analog.

## 5. Help / README / argparse

One sentence in `helptext` halt_flatten **and** cli sections, README Operator, and `paper kill --help`:

- Account kill on the Web requires typing `FLATTEN`.
- CLI account kill requires typing `FLATTEN` on a TTY, or `--force` when stdin is not a TTY.

`--force` help text: `skip account-kill confirmation (required when stdin is not a TTY)`.

Architecture explanation gets one sentence in the halt/flatten paragraph so C4 readers know the CLI gate exists. Do not add a new C4 box.

## 6. In / out

**In:** CLI account-kill TTY `FLATTEN` prompt; non-TTY fail-closed; `--force`; help/README/argparse; tests that prove no flatten on refuse.

**Out:** sleeve CLI confirm; `--yes`; treating non-TTY as yes; accepting piped `FLATTEN` without `--force`; API-level confirm; changing isolation math; live; sixth screen; Activity blotter copy (separate gap); Risk allocation clone.

## 7. Verification

- Unit: `confirm_account_kill(force=True)` proceeds; non-TTY without force returns 1 and writes the `--force` error; TTY + `FLATTEN` proceeds; TTY + `yes` / empty returns 1 and does not proceed.
- CLI: `paper kill` (no bundle, pytest non-TTY) exits 1, sleeve state unchanged, Alpaca adapter not used to flatten.
- CLI: `paper kill --force` (no bundle) exits 0 and prints account `KillOutcome` JSON (`reason` `account`, `flattened` true).
- CLI: `paper kill --bundle <id>` still works without `--force` (existing outcome JSON test).
- `paper kill --help` mentions `--force` and flatten.
- Help/README mention TTY `FLATTEN` and `--force`.
- SIGINT flatten helper still kills without a CLI flag.
- No real broker orders.
