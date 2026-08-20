"""Canonical operator how-to copy for CLI, API, and Quiet cockpit."""
from __future__ import annotations

from typing import Any

HELP_TITLE = "alphastrategy operator help"

SECTIONS: list[dict[str, str]] = [
    {
        "id": "identity",
        "title": "What this desk is",
        "body": (
            "alphastrategy is a local Alpaca paper execution desk. "
            "alphaloop searches and stress-tests candidates; this product runs "
            "qualified .asb bundles. Import is not permission to trade. Starting "
            "a paper sleeve is a second explicit human action."
        ),
    },
    {
        "id": "execution",
        "title": "How paper execution works",
        "body": (
            "The Supervisor is the sole order placer. Sleeve interpreters return "
            "target weights over stdin/stdout JSON and never see keys or the broker. "
            "Heartbeat every 20 seconds does not place orders. At most two RTH "
            "rebalances fire: open plus 3 minutes, and 12 minutes before close. "
            "combined[asset] = sum(allocation_i * weight_i[asset]). Residual is cash."
        ),
    },
    {
        "id": "halt_flatten",
        "title": "Halt is not flatten",
        "body": (
            "Halt is not flatten. Halt stops new orders and holds positions. "
            "Flatten cancels open orders and trades the paper account (or an "
            "isolated sleeve residual) toward flat. Stop zeros a sleeve on the "
            "next legal rebalance and does not flatten now. Resume after halt "
            "does not catch up; the next legal open or close rebalance does. "
            "Account kill on the Web requires typing FLATTEN. CLI account kill "
            "requires typing FLATTEN on a TTY, or --force when stdin is not a TTY. "
            "Sleeve kill reports whether isolation succeeded or the whole paper "
            "account was flattened. Desk banners stay visible on every screen."
        ),
    },
    {
        "id": "cockpit",
        "title": "Quiet cockpit",
        "body": (
            "Five screens: Portfolio, Strategies, Run, Activity, Risk. "
            "Wanted is the last combined target weight; Got is the current "
            "position weight. An empty desk says Start this paper desk and "
            "tells you to import, then start paper. Portfolio Book is wanted "
            "versus got. Gross utilization is against the account cap. Session and "
            "Next rebalance are Portfolio tiles. Cap is name weight versus the "
            "account single-name limit. Sleeves show spoken share of the paper book. "
            "Risk lists each sleeve allocation as text. A red FLAT banner means "
            "the paper account was flattened. Activity kill rows say isolated "
            "residual or flattened account. status includes last_kill even "
            "when the control plane is down. Alt+1 through Alt+5 switch screens. "
            "F1 toggles Help. Help is this aside, not a sixth screen."
        ),
    },
    {
        "id": "cli",
        "title": "CLI verbs",
        "body": (
            "alphastrategy start, import, status, paper start, paper stop, "
            "paper kill, paper resume. paper kill without --bundle flattens "
            "the whole paper account. That CLI account kill prompts for FLATTEN "
            "on a TTY and refuses on a non-TTY unless --force is passed. "
            "paper kill --bundle isolates when the "
            "last book is clean; otherwise it flattens the account rather than guess."
        ),
    },
    {
        "id": "walls",
        "title": "Hard walls",
        "body": (
            "Paper only. Control plane binds 127.0.0.1. No live toggle. "
            "No broker credentials in .asb files, logs, or the web UI."
        ),
    },
]


def help_payload() -> dict[str, Any]:
    return {"title": HELP_TITLE, "sections": [dict(section) for section in SECTIONS]}


def help_text() -> str:
    lines = [HELP_TITLE, ""]
    for section in SECTIONS:
        lines.append(section["title"])
        lines.append(section["body"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
