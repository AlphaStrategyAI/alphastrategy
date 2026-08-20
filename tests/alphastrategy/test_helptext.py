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
    from alphastrategy.helptext import SCREEN_HOWTOS

    blob = (
        help_text().lower()
        + " ".join(section["body"].lower() for section in SECTIONS)
        + " ".join(item["body"].lower() for item in SCREEN_HOWTOS)
    )
    assert "streamlit" not in blob
    assert "openstrategy" not in blob
    assert "live trading" not in blob
