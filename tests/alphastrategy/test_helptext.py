from __future__ import annotations

from alphastrategy.helptext import SECTIONS, help_payload, help_text

REQUIRED_IDS = (
    "identity",
    "execution",
    "halt_flatten",
    "cockpit",
    "cli",
    "walls",
)

REQUIRED_PHRASES = (
    "halt is not flatten",
    "paper only",
    "sole order placer",
    "does not catch up",
    "FLATTEN",
    "--force",
    "isolated residual",
    "Start this paper desk",
    "Alt+1",
    "Wanted",
    "Got",
    "Next rebalance",
    "Orders today",
    "utilization",
    "next action",
    "Supervisor beat",
    "Book / Flatten budgets / Clock",
    "Positions Book column",
    "Gross cap",
    "On Portfolio",
    "Flatten account",
    "own error",
    "assembled from js/",
    "Inventory / Import .asb / Roster",
    "Caps / Headroom / Tighten",
    "Beat / Tape / Blotter",
    "not a JSON dump",
    "How to import a qualified .asb",
    "empty Portfolio",
    "Book Drift",
    "Start paper after flatten",
    "Your first paper session",
    "Pulse / Age / Interval / Supervisor",
    "Pulse, Session, and Supervisor",
    "Remaining / Spoken / Active / Idle",
    "Spoken / Overlays / Tighter / Idle",
    "Gross cap / Name cap / Names / Orders today",
    "Names / Orders today / Cash / Target cash",
    "Rows / Wanted / Got / At cap",
    "Session / Now / Next / Last",
    "incomplete rebalance",
    "interrupted rebalancing",
    "interrupted flattening",
    "interrupted sleeve isolate",
    "After halt shows the halt reason",
    "flatten banner names interrupted flattening",
    "flatten banner names a limit breach",
    "flatten banner names the breached cap",
    "Tight / Delta $ / Delta % / Fields",
    "flushes the snapshot to disk before orders",
    "Tighten this sleeve",
    "audit and runtime overlays flush to disk",
    "Tighten this sleeve stays open across the refresh",
    "Clock Last names the spent window",
    "even with 0 fills",
    "Tape Rebalances sub names spent",
    "deviation banner follows Book Drift",
    "Roster names imported at",
    "import-meta flushes to disk",
    "How to read a spent window",
    "Clock Last is spent",
    "imported members flush to disk",
    "staging lives under imported/",
    "Session OPEN is halt color while Supervisor is HALTED",
    "Clock Next is held while Supervisor is HALTED",
    "Clock Next is flat while the paper account is flattened",
    "stale persist temps and import staging are removed on start",
    "Start paper while halted waits for resume",
    "Tighten that breaches the live book flattens now",
    "Each sleeve card names imported, paper, halted, or stopped",
    "A sleeve overlay that breaches the live book flattens now",
    "Caps is the spoken book",
    "Heartbeat refreshes last prices and does not flatten",
    "Rebalance flattens a live book that already breaches the spoken cap",
    "Book Drift follows the last fill, not last prices",
)


def test_section_ids_in_order() -> None:
    assert tuple(section["id"] for section in SECTIONS) == REQUIRED_IDS


def test_help_payload_matches_sections() -> None:
    payload = help_payload()
    assert payload["title"] == "alphastrategy operator help"
    assert payload["sections"] == SECTIONS
    for section in payload["sections"]:
        assert section["title"].strip()
        assert section["body"].strip()


def test_screen_howtos_match_five_screens() -> None:
    from alphastrategy.helptext import SCREEN_HOWTOS

    howto_screens = ("portfolio", "strategies", "run", "activity", "risk")
    howto_ids = (
        "how_portfolio",
        "how_strategies",
        "how_run",
        "how_activity",
        "how_risk",
    )
    assert tuple(item["screen"] for item in SCREEN_HOWTOS) == howto_screens
    assert tuple(item["id"] for item in SCREEN_HOWTOS) == howto_ids
    payload = help_payload()
    assert payload["howtos"] == SCREEN_HOWTOS
    ids = [section["id"] for section in payload["sections"]]
    assert ids == list(REQUIRED_IDS)
    text = help_text()
    assert "On Portfolio" in text
    assert "On Run" in text
    assert "Full runbook" not in text
    assert "halt is not flatten" in text.lower()


def test_help_text_contains_required_phrases() -> None:
    text = help_text()
    lower = text.lower()
    assert "halt is not flatten" in lower
    for phrase in REQUIRED_PHRASES:
        if phrase == "FLATTEN":
            assert "FLATTEN" in text
        elif phrase == "--force":
            assert "--force" in text
        elif phrase in ("Wanted", "Got", "Next rebalance"):
            assert phrase in text
        else:
            assert phrase.lower() in lower


def test_help_copy_is_this_product() -> None:
    from alphastrategy.helptext import SCREEN_HOWTOS, TASK_HOWTOS, TUTORIALS

    blob = (
        help_text().lower()
        + " ".join(section["body"].lower() for section in SECTIONS)
        + " ".join(item["body"].lower() for item in SCREEN_HOWTOS)
        + " ".join(item["body"].lower() for item in TASK_HOWTOS)
        + " ".join(item["body"].lower() for item in TUTORIALS)
    )
    assert "streamlit" not in blob
    assert "openstrategy" not in blob
    assert "live trading" not in blob


def test_task_howtos_match_jobs() -> None:
    from alphastrategy.helptext import TASK_HOWTOS

    assert tuple(item["id"] for item in TASK_HOWTOS) == (
        "task_import",
        "task_start",
        "task_flatten",
        "task_tighten",
        "task_wanted",
        "task_spent",
    )
    payload = help_payload()
    assert payload["tasks"] == TASK_HOWTOS
    assert payload["howtos"][0]["id"] == "how_portfolio"
    text = help_text()
    assert text.index("How to import a qualified .asb") < text.index("On Portfolio")
    for item in TASK_HOWTOS:
        assert item["title"].startswith("How to")
        assert item["body"].strip()
        assert item["screens"]
        for screen in item["screens"]:
            assert screen in ("portfolio", "strategies", "run", "activity", "risk")


def test_tutorials_come_before_how_to_jobs() -> None:
    from alphastrategy.helptext import TUTORIALS

    assert tuple(item["id"] for item in TUTORIALS) == ("tutorial_first_session",)
    payload = help_payload()
    assert payload["tutorials"] == TUTORIALS
    item = TUTORIALS[0]
    assert item["title"] == "Your first paper session"
    assert not item["title"].startswith("How to")
    assert "You will see" in item["body"]
    assert "You finished the lesson" in item["body"]
    assert "Flatten account" in item["body"]
    assert "Roster names imported at" in item["body"]
    assert "Session / Now / Next / Last" in item["body"]
    assert "Next rebalance" in item["body"]
    text = help_text()
    assert text.index("Your first paper session") < text.index(
        "How to import a qualified .asb"
    )
