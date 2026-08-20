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


@pytest.fixture
def js_text() -> str:
    return JS_PATH.read_text(encoding="utf-8")


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


def test_html_has_control_plane_banner(html_text: str) -> None:
    assert 'id="control-plane-banner"' in html_text
    assert 'id="account-kill-phrase"' in html_text
    assert 'id="account-kill-confirm"' in html_text
    assert "Contribution" in html_text
    assert "Notional" in html_text
    assert "Wanted" in html_text


def test_js_renders_countdown_and_stopped(js_text: str) -> None:
    assert "countdown" in js_text
    assert "fmtCountdown" in js_text
    assert "sleeve_contribution" in js_text
    assert "stopped" in js_text
    assert "FLATTEN" in js_text
    assert "control-plane-banner" in js_text
    assert "riskFormIsDirty" in js_text
    assert "expanded" in js_text


def test_html_has_flatten_banner_and_wanted_column(html_text: str) -> None:
    assert 'id="flatten-banner"' in html_text
    assert "Wanted" in html_text
    assert "Got" in html_text


def test_js_renders_flatten_banner(js_text: str) -> None:
    assert "flatten-banner" in js_text
    assert "flattened" in js_text
    assert "wanted" in js_text


def test_html_help_is_aside_not_sixth_nav(html_text: str) -> None:
    assert 'id="help-toggle"' in html_text
    assert 'id="help-panel"' in html_text
    assert 'aria-controls="help-panel"' in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    assert nav is not None
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]
    assert "help" not in screens
    assert 'data-screen="help"' not in html_text


def test_js_fetches_help_and_toggles_panel(js_text: str) -> None:
    assert "/api/help" in js_text
    assert "help-toggle" in js_text
    assert "help-panel" in js_text
    assert "aria-expanded" in js_text
    assert "Escape" in js_text


def test_css_help_panel_is_aside_not_modal(css_text: str) -> None:
    assert "#help-panel" in css_text
    panel = re.search(r"#help-panel\s*\{[^}]*\}", css_text)
    assert panel is not None
    block = panel.group(0).lower()
    assert "position: fixed" not in block
    assert "#11151d" in css_text


def test_js_run_sleeve_allocation_and_kill_confirm(js_text: str) -> None:
    assert "sleeve-alloc-form" in js_text
    assert "Confirm paper allocation" in js_text
    assert "Set allocation" in js_text
    assert "data-kill-confirm" in js_text
    assert "Confirm sleeve kill" in js_text
    assert "runFormIsDirty" in js_text
    assert "Confirm paper allocation required" in js_text
    assert "window.confirm" not in js_text
    assert "/api/paper/start" in js_text
    assert "box.checked = false" in js_text
    assert "dataset.current" in js_text


def test_html_desk_banners_outside_portfolio(html_text: str) -> None:
    desk_at = html_text.find('id="desk-banners"')
    portfolio_at = html_text.find('id="screen-portfolio"')
    assert desk_at != -1
    assert 0 <= desk_at < portfolio_at
    for banner_id in (
        "halt-banner",
        "flatten-banner",
        "deviation-banner",
        "control-plane-banner",
        "kill-outcome-banner",
    ):
        assert html_text.find(f'id="{banner_id}"') < portfolio_at
        assert html_text.count(f'id="{banner_id}"') == 1


def test_js_renders_kill_outcome_from_last_kill(js_text: str) -> None:
    assert "kill-outcome-banner" in js_text
    assert "last_kill" in js_text
    assert "SLEEVE KILL: isolated residual" in js_text
    assert "could not isolate" in js_text
    assert "unknown sleeve" in js_text

def test_js_sleeve_kill_does_not_require_flatten_phrase(js_text: str) -> None:
    kill_fn = js_text.split("async function killSleeve")[1].split("async function onImportSubmit")[0]
    assert "FLATTEN" not in kill_fn
    assert "data-kill-confirm" in js_text


def test_js_activity_kill_summary_distinguishes_isolated(js_text: str) -> None:
    kill_branch = js_text.split('case "kill":')[1].split('case "flatten":')[0]
    assert "isolated residual" in kill_branch
    assert "flattened account" in kill_branch
    assert "ev.isolated" in kill_branch
