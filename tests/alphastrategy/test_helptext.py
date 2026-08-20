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
    blob = help_text().lower() + " ".join(section["body"].lower() for section in SECTIONS)
    assert "streamlit" not in blob
    assert "openstrategy" not in blob
    assert "live trading" not in blob
