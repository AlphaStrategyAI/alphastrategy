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
            "Flatten clears the last book and zeros live sleeves. "
            "Start paper after flatten starts the session loop again and "
            "does not catch up. Resume is only after halt. "
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
            "position weight. An empty Portfolio shows Start this paper desk "
            "as its first glance band, not a global panel. Portfolio home is three "
            "bands Book / Flatten budgets / Clock. Equity is the hero. "
            "Book Drift is names off the last combined target. "
            "Positions include wanted names with no fill. "
            "Strategies is three bands Inventory / Import .asb / Roster. "
            "Paper is the hero count. "
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
            "Risk is four bands Caps / Headroom / Tighten plus Sleeve overlays. "
            "Tighten still posts the policy keys. "
            "Risk lists each sleeve allocation as text. A red FLAT banner means "
            "the paper account was flattened. Activity kill rows say isolated "
            "residual or flattened account. status includes last_kill even "
            "when the control plane is down. Activity empty copy names the two "
            "legal rebalances. Activity is three bands Beat / Tape / Blotter. "
            "Beat is Pulse / Age / Interval / Supervisor. "
            "Expanding a blotter row shows Wanted versus Got, not a JSON dump. "
            "Header shows Pulse, Session, and Supervisor. "
            "Header LIVE is the Supervisor beat, not Session. "
            "Alt+1 through Alt+5 switch screens. "
            "F1 opens Help. Help starts with Your first paper session, then "
            "the screen how-to and the jobs for that screen. The six runbook sections "
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
            "Empty Portfolio starts with Start this paper desk, then "
            "three bands: Book / Flatten budgets / Clock. Equity is the hero. "
            "Book Drift is names off the last combined target. "
            "Positions include wanted names with no fill. "
            "The Positions Book column is wanted versus got. "
            "Header LIVE is the Supervisor beat, not Session OPEN."
        ),
    },
    {
        "id": "how_strategies",
        "screen": "strategies",
        "title": "On Strategies",
        "body": (
            "Three bands: Inventory / Import .asb / Roster. Paper is the hero count. "
            "The four tiles are imported, paper, halted, and stopped. "
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
            "Three bands: Beat / Tape / Blotter. "
            "Beat is four tiles Pulse / Age / Interval / Supervisor. Pulse is the hero. "
            "Rebalances is the hero count. "
            "Halt, deviation, and kill tiles are not quiet when above zero. "
            "Time-ordered audit. Empty copy names the two legal rebalances. "
            "Kill rows say isolated residual or flattened account. "
            "Expand a blotter row for a Wanted / Got table, not a JSON dump."
        ),
    },
    {
        "id": "how_risk",
        "screen": "risk",
        "title": "On Risk",
        "body": (
            "Four bands: Caps / Headroom / Tighten, then Sleeve overlays. "
            "Account totals stay sticky. "
            "Tighten groups Gross / Names / Orders / Deltas. Tighten only; "
            "the form refuses looser values and still posts the policy keys."
        ),
    },
]


TUTORIALS: list[dict[str, str]] = [
    {
        "id": "tutorial_first_session",
        "title": "Your first paper session",
        "body": (
            "This lesson walks one paper session. You will import a qualified .asb "
            "and start a sleeve. You will not flatten. "
            "1. Run alphastrategy start and open the Quiet cockpit. "
            "You will see empty Portfolio: Start this paper desk, then Book / Flatten budgets / Clock. "
            "2. Open Strategies (Alt+2). Under Import .asb upload the file. "
            "You will see Inventory Imported count 1. You are not trading yet. "
            "3. Open Run (Alt+3). Under Start paper pick the bundle, set a small allocation, "
            "check Confirm paper start, then Start paper. "
            "You will see the sleeve on Run. Portfolio Clock shows Session and Next rebalance. "
            "4. Open Portfolio Positions. Empty rows until the next legal rebalance are expected. "
            "Book Drift stays an em dash or 0 until then. "
            "You finished the lesson when the sleeve is on Run and Clock shows Next rebalance. "
            "Do not use Flatten account in this lesson."
        ),
    },
]


TASK_HOWTOS: list[dict[str, Any]] = [
    {
        "id": "task_import",
        "screens": ["strategies"],
        "title": "How to import a qualified .asb",
        "body": (
            "1. Open Strategies (Alt+2). "
            "2. Under Import .asb choose the file and Upload. "
            "3. If rejected, the gate (hash, schema, conformance) and a next action are named. "
            "Import is not permission to trade."
        ),
    },
    {
        "id": "task_start",
        "screens": ["strategies", "run"],
        "title": "How to start a paper sleeve",
        "body": (
            "1. Import first if Inventory is empty. "
            "2. Open Run (Alt+3). "
            "3. Under Start paper pick the bundle, set allocation, check Confirm paper start, then Start paper. "
            "This is the second explicit action. "
            "Start paper after flatten starts the session loop again and does not catch up."
        ),
    },
    {
        "id": "task_flatten",
        "screens": ["run"],
        "title": "How to flatten the paper account",
        "body": (
            "1. Open Run (Alt+3). "
            "2. Under Flatten account — not After halt — check the box, type FLATTEN, then Kill account. "
            "Halt is not flatten. Resume does not catch up."
        ),
    },
    {
        "id": "task_tighten",
        "screens": ["risk"],
        "title": "How to tighten a cap",
        "body": (
            "1. Open Risk (Alt+5). "
            "2. Caps and Headroom stay sticky. "
            "3. Under Tighten change only Gross / Names / Orders / Deltas fields you mean to tighten, then Tighten. "
            "Looser values are refused; PUT keys stay machine names."
        ),
    },
    {
        "id": "task_wanted",
        "screens": ["portfolio", "activity"],
        "title": "How to read wanted versus got",
        "body": (
            "1. On Portfolio, Positions Wanted versus Got is last combined target versus current weight. "
            "2. On Activity, expand a rebalance blotter row for the Wanted / Got table, not a JSON dump."
        ),
    },
]


def help_payload() -> dict[str, Any]:
    return {
        "title": HELP_TITLE,
        "sections": [dict(section) for section in SECTIONS],
        "howtos": [dict(item) for item in SCREEN_HOWTOS],
        "tasks": [dict(item) for item in TASK_HOWTOS],
        "tutorials": [dict(item) for item in TUTORIALS],
    }


def help_text() -> str:
    lines = [HELP_TITLE, ""]
    for item in TUTORIALS:
        lines.append(item["title"])
        lines.append(item["body"])
        lines.append("")
    for item in TASK_HOWTOS:
        lines.append(item["title"])
        lines.append(item["body"])
        lines.append("")
    for item in SCREEN_HOWTOS:
        lines.append(item["title"])
        lines.append(item["body"])
        lines.append("")
    for section in SECTIONS:
        lines.append(section["title"])
        lines.append(section["body"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
