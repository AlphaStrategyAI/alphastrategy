from __future__ import annotations

import re
from pathlib import Path

import pytest

STATIC_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "alphastrategy" / "web" / "static"
)
HTML_PATH = STATIC_DIR / "index.html"
CSS_PATH = STATIC_DIR / "styles.css"
JS_PATH = STATIC_DIR / "app.js"

NAV_LABELS = ("Portfolio", "Strategies", "Run", "Activity", "Risk")

CSS_TOKENS = (
    "#0b0e14",
    "#11151d",
    "#2a3142",
    "#e5e9f0",
    "#5c6573",
    "#9ba3b4",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "system-ui",
    "tabular-nums",
)

LIVE_PATTERNS = [
    re.compile(r"confirm_live"),
    re.compile(r"paper\s*=\s*false", re.IGNORECASE),
    re.compile(r"['\"]paper['\"]\s*:\s*false", re.IGNORECASE),
    re.compile(r"live\s*toggle", re.IGNORECASE),
    re.compile(r"id=['\"]live['\"]", re.IGNORECASE),
    re.compile(r"class=['\"][^'\"]*live-toggle", re.IGNORECASE),
]


@pytest.fixture
def html_text() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


@pytest.fixture
def css_text() -> str:
    return CSS_PATH.read_text(encoding="utf-8")


def test_static_files_exist() -> None:
    assert HTML_PATH.is_file()
    assert CSS_PATH.is_file()
    assert JS_PATH.is_file()


def test_css_contains_locked_tokens(css_text: str) -> None:
    lowered = css_text.lower()
    for token in CSS_TOKENS:
        assert token.lower() in lowered, f"missing CSS token: {token}"


def test_css_halt_banner_uses_halt_color(css_text: str) -> None:
    assert ".halt" in css_text
    halt_block = re.search(r"\.halt\s*\{[^}]*\}", css_text, re.DOTALL)
    assert halt_block is not None
    assert "#f59e0b" in halt_block.group(0).lower()


def test_html_contains_five_nav_labels(html_text: str) -> None:
    for label in NAV_LABELS:
        assert label in html_text


def test_html_nav_labels_exact_set(html_text: str) -> None:
    found = [label for label in NAV_LABELS if label in html_text]
    assert found == list(NAV_LABELS)


def test_html_has_no_live_controls(html_text: str) -> None:
    for pattern in LIVE_PATTERNS:
        assert not pattern.search(html_text), f"forbidden pattern in HTML: {pattern.pattern}"


def test_html_has_no_live_toggle_label(html_text: str) -> None:
    assert not re.search(r">\s*Live\s*<", html_text)
