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
            "a paper sleeve is a second explicit human action. Import failures "
            "name the gate (hash, schema, conformance) and a next action."
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
            "combined[asset] = sum(allocation_i * weight_i[asset]). Residual is cash. "
            "Header LIVE, STALE, or DEAD is the Supervisor beat, not RTH Session OPEN."
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
            "tells you to import, then start paper. Portfolio home is three "
            "bands Book / Flatten budgets / Clock. Equity is the hero. "
            "Positions and Sleeves sit side by side on a wide desk. "
            "The Positions Book column is wanted versus got. Gross utilization "
            "is against "
            "the account cap. Session and Next rebalance are the Clock tiles. "
            "Cap is name weight versus the "
            "account single-name limit. Names and Orders today are remaining "
            "flatten budgets. Cash shows invested versus residual against the "
            "last combined target. status includes utilization. "
            "Sleeves show spoken share of the paper book. "
            "Risk names caps in desk words (Gross cap, Names, Orders today). "
            "Tighten still posts the policy keys. "
            "Risk lists each sleeve allocation as text. A red FLAT banner means "
            "the paper account was flattened. Activity kill rows say isolated "
            "residual or flattened account. status includes last_kill even "
            "when the control plane is down. Activity empty copy names the two "
            "legal rebalances. Header LIVE is the Supervisor beat, not Session. "
            "Alt+1 through Alt+5 switch screens. "
            "F1 is how-to for the current screen. The six runbook sections "
            "match alphastrategy help. "
            "Quiet cockpit JS is assembled from js/ parts. The browser still "
            "loads /app.js. "
            "Help is this aside, not a sixth screen."
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


SCREEN_HOWTOS: list[dict[str, str]] = [
    {
        "id": "how_portfolio",
        "screen": "portfolio",
        "title": "On Portfolio",
        "body": (
            "Three bands: Book / Flatten budgets / Clock. Equity is the hero. "
            "The Positions Book column is wanted versus got. "
            "Header LIVE is the Supervisor beat, not Session OPEN."
        ),
    },
    {
        "id": "how_strategies",
        "screen": "strategies",
        "title": "On Strategies",
        "body": (
            "Upload a qualified .asb. Import is not permission to trade. "
            "Failures name the gate (hash, schema, conformance) and a next action. "
            "Start paper on Run."
        ),
    },
    {
        "id": "how_run",
        "screen": "run",
        "title": "On Run",
        "body": (
            "Run is four bands: Start paper, Sleeves, After halt, Flatten account. "
            "Start paper is a second explicit action. "
            "Stop zeros that sleeve on the next legal rebalance and does not flatten now. "
            "Sleeve kill flattens that sleeve, or the whole account if isolation is unclean. "
            "Resume lives under After halt and does not catch up. "
            "Account kill lives under Flatten account and requires typing FLATTEN. "
            "Each Run band shows its own error."
        ),
    },
    {
        "id": "how_activity",
        "screen": "activity",
        "title": "On Activity",
        "body": (
            "Time-ordered audit. Empty copy names the two legal rebalances. "
            "Kill rows say isolated residual or flattened account. "
            "Expand a row for the payload."
        ),
    },
    {
        "id": "how_risk",
        "screen": "risk",
        "title": "On Risk",
        "body": (
            "Account caps stay visible. Caps use desk words "
            "(Gross cap, Names, Orders today). Tighten only; "
            "the form refuses looser values and still posts the policy keys."
        ),
    },
]


def help_payload() -> dict[str, Any]:
    return {
        "title": HELP_TITLE,
        "sections": [dict(section) for section in SECTIONS],
        "howtos": [dict(item) for item in SCREEN_HOWTOS],
    }


def help_text() -> str:
    lines = [HELP_TITLE, ""]
    for item in SCREEN_HOWTOS:
        lines.append(item["title"])
        lines.append(item["body"])
        lines.append("")
    for section in SECTIONS:
        lines.append(section["title"])
        lines.append(section["body"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
