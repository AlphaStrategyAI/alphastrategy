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
            "Heartbeat every 20 seconds does not place orders. "
            "Heartbeat refreshes last prices and does not flatten. "
            "Heartbeat seeds the live book glance. "
            "A heartbeat live book holds until flatten or place. "
            "Tighten and Start paper flatten the same live book as Book. "
            "Caps LIMIT follows the same live book as Tighten. "
            "Runtime overlays load once until the file changes. "
            "Tighten PUT reads runtime overlays from the Supervisor. "
            "At most two RTH rebalances fire: open plus 3 minutes, and 12 minutes before close. "
            "combined[asset] = sum(allocation_i * weight_i[asset]). Residual is cash. "
            "An incomplete rebalance still writes Wanted / Got, counts those orders, "
            "and health-halts. It does not flatten and does not retry that event. "
            "If the host dies mid-rebalance, the desk treats that as interrupted "
            "rebalancing: it writes Wanted / Got from the broker, health-halts, "
            "and does not flatten or retry that event. "
            "Persist-before-send flushes the snapshot to disk before orders so a "
            "host kill still sees REBALANCING, FLATTENING, or isolate_in_flight. "
            "Persist-before-send spends the session event even with 0 fills. "
            "Clock Last names the spent window. "
            "Audit and runtime overlays flush to disk with that snapshot family. "
            "import-meta flushes to disk with that snapshot family. "
            "Imported members flush to disk. Staging lives under imported/. "
            "Stale persist temps and import staging are removed on start. "
            "Header LIVE, STALE, or DEAD is the Supervisor beat, not RTH Session OPEN."
        ),
    },
    {
        "id": "halt_flatten",
        "title": "Halt is not flatten",
        "body": (
            "Halt is not flatten. Halt stops new orders and holds positions. "
            "If the host dies while flattening, the desk treats that as "
            "interrupted flattening: it retries cancel and close_all. If the "
            "broker is unreachable it health-halts. "
            "The flatten banner names interrupted flattening when the host died "
            "mid-close_all. "
            "The flatten banner names a limit breach when a cap flattened the "
            "paper account. The flatten banner names the breached cap in desk "
            "words (Gross cap, Name cap, Names, Orders today). "
            "Tighten that breaches the live book flattens now. "
            "Tighten and Start paper flatten the same live book as Book. "
            "Caps LIMIT follows the same live book as Tighten. "
            "Tighten PUT reads runtime overlays from the Supervisor. "
            "A sleeve overlay that breaches the live book flattens now. "
            "Rebalance flattens a live book that already breaches the spoken cap. "
            "A live book through the spoken cap warns before the next rebalance flattens. "
            "Activity flatten rows say limit breach or that cap plus breach. "
            "If the host dies during a sleeve isolate, the desk treats that as "
            "interrupted sleeve isolate: it flattens the whole paper account "
            "rather than guess the residual. "
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
            "as its first glance band, not a global panel. Portfolio home is "
            "Book / Flatten budgets / Clock, then Positions / Sleeves. "
            "Positions is Rows / Wanted / Got / At cap. Equity is the hero. "
            "Day PnL is equity minus last close. "
            "Clock is Session / Now / Next / Last. "
            "Book Drift is names off the last combined target. "
            "Book Drift follows the last fill, not last prices. "
            "A live book through the spoken cap warns before the next rebalance flattens. "
            "The deviation banner follows Book Drift and cannot go quiet while Drift is above zero. "
            "A spent window keeps it. "
            "Positions include wanted names with no fill. "
            "Strategies is three bands Inventory / Import .asb / Roster. "
            "Paper is the hero count. "
            "Positions and Sleeves sit side by side on a wide desk. "
            "The Positions Book column is wanted versus got. Gross utilization "
            "is against the spoken flatten cap. Session and Next rebalance are the Clock tiles. "
            "Cap is name weight versus the spoken single-name limit. Names and Orders today are remaining "
            "flatten budgets. Cash shows invested versus residual against the "
            "last combined target. status includes utilization. "
            "Sleeves show spoken share of the paper book. "
            "Run Sleeves is Remaining / Spoken / Active / Idle. "
            "Risk names caps in desk words (Gross cap, Names, Orders today). "
            "Caps is Gross cap / Name cap / Names / Orders today. "
            "Caps is the spoken book. Tighten still edits the account form. "
            "Caps names the cap the live book is through. "
            "Spoken policy is reused until overlays or allocations change. "
            "Status, Portfolio, and Risk share one live book glance. "
            "A heartbeat live book holds until flatten or place. "
            "Runtime overlays load once until the file changes. "
            "Headroom is Names / Orders today / Cash / Target cash. "
            "Risk is four bands Caps / Headroom / Tighten plus Sleeve overlays. "
            "Tighten is Tight / Delta $ / Delta % / Fields. "
            "Tighten still posts the policy keys. "
            "Risk lists sleeve overlays as Spoken / Overlays / Tighter / Idle. "
            "Each overlay card is allocation rail and tighter count; Tighten this sleeve holds the form. "
            "Tighten this sleeve stays open across the refresh until you close it. "
            "A red FLAT banner means "
            "the paper account was flattened. Activity kill rows say isolated "
            "residual or flattened account. status includes last_kill even "
            "when the control plane is down. Activity empty copy names the two "
            "legal rebalances. Activity is three bands Beat / Tape / Blotter. "
            "Beat is Pulse / Age / Interval / Supervisor. "
            "Expanding a blotter row shows Wanted versus Got, not a JSON dump. "
            "Header shows Pulse, Session, and Supervisor. "
            "Header LIVE is the Supervisor beat, not Session. "
            "Session OPEN is halt color while Supervisor is HALTED. "
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
            "last book is clean; otherwise it flattens the account rather than guess. "
            "status names LIMIT while the live book is through the spoken cap. "
            "status names BOOK heartbeat or glance. "
            "status names Day PnL. "
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
            "Book / Flatten budgets / Clock, then Positions / Sleeves. Equity is the hero. "
            "Book Drift is names off the last combined target. "
            "Book Drift follows the last fill, not last prices. "
            "A live book through the spoken cap warns before the next rebalance flattens. "
            "The deviation banner follows Book Drift and cannot go quiet while Drift is above zero. "
            "A spent window keeps it. "
            "Positions is four tiles Rows / Wanted / Got / At cap. Wanted is the hero. "
            "Clock is four tiles Session / Now / Next / Last. Next is the hero. "
            "Clock Last names the spent window when that event did not finish. "
            "Clock Next is held while Supervisor is HALTED. "
            "Clock Next is flat while the paper account is flattened. "
            "Clock Next is flatten while the live book is through the spoken cap. "
            "Status, Portfolio, and Risk share one live book glance. "
            "A heartbeat live book holds until flatten or place. "
            "Runtime overlays load once until the file changes. "
            "Book Equity names Beat or Glance. "
            "Book, Beat, and Headroom name Beat or Glance. "
            "Day PnL is equity minus last close. "
            "Positions include wanted names with no fill. "
            "The Positions Book column is wanted versus got. "
            "Header LIVE is the Supervisor beat, not Session OPEN. "
            "Session OPEN is halt color while Supervisor is HALTED."
        ),
    },
    {
        "id": "how_strategies",
        "screen": "strategies",
        "title": "On Strategies",
        "body": (
            "Three bands: Inventory / Import .asb / Roster. Paper is the hero count. "
            "The four tiles are imported, paper, halted, and stopped. "
            "Roster names imported at. "
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
            "Sleeves is four tiles Remaining / Spoken / Active / Idle. Remaining is the hero. "
            "Each sleeve card names imported, paper, halted, or stopped. Allocation is a rail. "
            "Start paper is a second explicit action. "
            "Start paper while halted waits for resume. Resume does not catch up. "
            "A sleeve overlay that breaches the live book flattens now. "
            "Start paper that flattens names the breached cap. "
            "Stop zeros that sleeve on the next legal rebalance and does not flatten now. "
            "Sleeve kill flattens that sleeve, or the whole account if isolation is unclean. "
            "Resume lives under After halt and does not catch up. "
            "After halt shows the halt reason. "
            "After halt names the spent session event. "
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
            "Book, Beat, and Headroom name Beat or Glance. "
            "Heartbeat refreshes last prices and does not flatten. "
            "Heartbeat seeds the live book glance. "
            "A heartbeat live book holds until flatten or place. "
            "Runtime overlays load once until the file changes. "
            "Rebalances is the hero count. "
            "Tape Rebalances sub names spent. "
            "Blotter rebalance rows say spent when that event did not finish. "
            "Halt, deviation, and kill tiles are not quiet when above zero. "
            "Time-ordered audit. Empty copy names the two legal rebalances. "
            "Kill rows say isolated residual or flattened account. "
            "Flatten rows say interrupted flattening or limit breach. "
            "The flatten banner names the breached cap. "
            "Expand a blotter row for a Wanted / Got table, not a JSON dump."
        ),
    },
    {
        "id": "how_risk",
        "screen": "risk",
        "title": "On Risk",
        "body": (
            "Four bands: Caps / Headroom / Tighten, then Sleeve overlays. "
            "Caps is four tiles Gross cap / Name cap / Names / Orders today. Gross cap is the hero. "
            "Caps is the spoken book. Tighten still edits the account form. "
            "Caps names the cap the live book is through. "
            "Spoken policy is reused until overlays or allocations change. "
            "Risk overlays load runtime once per glance. "
            "Sleeve envelopes load once until the file changes. "
            "Runtime overlays load once until the file changes. "
            "Tighten PUT reads runtime overlays from the Supervisor. "
            "Headroom is four tiles Names / Orders today / Cash / Target cash. Names is the hero. "
            "Book, Beat, and Headroom name Beat or Glance. "
            "Tighten is four tiles Tight / Delta $ / Delta % / Fields. Tight is the hero. "
            "Tight counts account caps stricter than v1 defaults. "
            "Delta $ and Delta % are skip floors Caps does not show. "
            "Sleeve overlays is four tiles Spoken / Overlays / Tighter / Idle. Spoken is the hero. "
            "Allocation is a rail, not only text. "
            "Each overlay card is allocation rail and tighter count; Tighten this sleeve holds the form. "
            "Tighten this sleeve stays open across the refresh until you close it. "
            "Account totals stay sticky. "
            "Tighten groups Gross / Names / Orders / Deltas. Tighten only; "
            "the form refuses looser values and still posts the policy keys. "
            "Tighten that breaches the live book flattens now. "
            "Tighten and Start paper flatten the same live book as Book. "
            "Caps LIMIT follows the same live book as Tighten. "
            "A sleeve overlay that breaches the live book flattens now. "
            "Rebalance flattens a live book that already breaches the spoken cap."
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
            "You will see Inventory Imported count 1. Roster names imported at. "
            "You are not trading yet. "
            "3. Open Run (Alt+3). Under Start paper pick the bundle, set a small allocation, "
            "check Confirm paper start, then Start paper. "
            "You will see the sleeve on Run. Clock is Session / Now / Next / Last. "
            "Next is the hero. Portfolio Clock shows Next rebalance. "
            "Last stays an em dash until a session event is spent or finishes. "
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
            "Start paper after flatten starts the session loop again and does not catch up. "
            "Start paper while halted waits for resume. Resume does not catch up. "
            "A sleeve overlay that breaches the live book flattens now. "
            "Tighten and Start paper flatten the same live book as Book."
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
            "Looser values are refused; PUT keys stay machine names. "
            "Tighten that breaches the live book flattens now. "
            "Tighten and Start paper flatten the same live book as Book. "
            "Caps LIMIT follows the same live book as Tighten. "
            "Tighten PUT reads runtime overlays from the Supervisor. "
            "A sleeve overlay that breaches the live book flattens now."
        ),
    },
    {
        "id": "task_wanted",
        "screens": ["portfolio", "activity"],
        "title": "How to read wanted versus got",
        "body": (
            "1. On Portfolio, Positions Wanted versus Got is last combined target versus current weight. "
            "Got is the current mark. Book Drift follows the last fill, not last prices. "
            "2. On Activity, expand a rebalance blotter row for the Wanted / Got table, not a JSON dump."
        ),
    },
    {
        "id": "task_spent",
        "screens": ["portfolio", "activity", "run"],
        "title": "How to read a spent window",
        "body": (
            "1. On Portfolio, Clock Last names the spent window. "
            "2. On Activity, Tape Rebalances sub names spent. "
            "3. The deviation banner follows Book Drift and cannot go quiet while "
            "Drift is above zero. "
            "4. On Run, After halt names the spent session event. "
            "Resume does not catch up. Clock Last is spent until a later event finishes."
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
