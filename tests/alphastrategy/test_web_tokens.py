from __future__ import annotations

import re
from pathlib import Path

import pytest

STATIC_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "alphastrategy" / "web" / "static"
)
HTML_PATH = STATIC_DIR / "index.html"
CSS_PATH = STATIC_DIR / "styles.css"

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
    from alphastrategy.web.cockpit import cockpit_js

    return cockpit_js()


def test_static_files_exist() -> None:
    from alphastrategy.web.cockpit import JS_PARTS

    assert HTML_PATH.is_file()
    assert CSS_PATH.is_file()
    for rel in JS_PARTS:
        assert (STATIC_DIR / rel).is_file(), rel
    assert not (STATIC_DIR / "app.js").is_file()


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
    assert "fallback_interrupted" in js_text
    assert "interrupted sleeve isolate — whole paper account flattened" in js_text

def test_js_sleeve_kill_does_not_require_flatten_phrase(js_text: str) -> None:
    start = js_text.index("async function killSleeve")
    nxt = js_text.find("\n  async function ", start + 1)
    kill_fn = js_text[start : nxt if nxt != -1 else None]
    assert "FLATTEN" not in kill_fn
    assert "data-kill-confirm" in js_text


def test_js_activity_kill_summary_distinguishes_isolated(js_text: str) -> None:
    kill_branch = js_text.split('case "kill":')[1].split('case "flatten":')[0]
    assert "isolated residual" in kill_branch
    assert "flattened account" in kill_branch
    assert "ev.isolated" in kill_branch
    assert "fallback_interrupted" in kill_branch
    assert "interrupted sleeve isolate" in kill_branch


def test_html_first_run_and_book_column(html_text: str) -> None:
    assert 'id="first-run"' in html_text
    port = html_text[
        html_text.find('id="screen-portfolio"') : html_text.find('id="screen-strategies"')
    ]
    assert 'id="first-run"' in port
    assert port.find('id="first-run"') < port.find('id="glance-book"')
    banners = html_text[
        html_text.find('id="desk-banners"') : html_text.find('id="screen-portfolio"')
    ]
    assert 'id="first-run"' not in banners
    assert '<h2 class="glance-heading">Start this paper desk</h2>' in port
    assert "Import is not permission to trade" in html_text
    assert 'data-go-screen="strategies"' in html_text
    assert 'data-go-screen="run"' in html_text
    assert ">Book<" in html_text
    assert 'id="metric-gross-bar"' in html_text
    assert 'id="metric-drift"' in html_text
    book = html_text[
        html_text.find('id="glance-book"') : html_text.find('id="glance-risk"')
    ]
    assert 'id="metric-drift"' in book
    assert "metrics-4" in book


def test_css_first_glance_tracks_use_locked_tokens(css_text: str) -> None:
    assert ".first-run" in css_text
    assert ".wg-track" in css_text
    assert ".util-track" in css_text
    assert ".wg-wanted" in css_text
    first = re.search(r"\.first-run\s*\{[^}]*\}", css_text)
    assert first is not None
    assert "#10b981" in first.group(0).lower()


def test_js_renders_book_drift(js_text: str) -> None:
    assert "function renderBookDrift" in js_text
    assert "metric-drift" in js_text
    assert "window.confirm" not in js_text


def test_js_first_glance_behaviors(js_text: str) -> None:
    assert "function renderFirstRun" in js_text
    assert "function wantedGotBar" in js_text
    assert "function renderGrossUtilization" in js_text
    assert "data-go-screen" in js_text
    assert "No positions yet. Import a .asb to begin." in js_text
    assert "Imported bundles are not trading. Start paper on Run." in js_text
    assert "The next legal open or close rebalance will trade." in js_text
    paint = js_text[
        js_text.find("function renderPortfolio") : js_text.find("function pulseLabel")
    ]
    assert "Clock Last is spent. Resume does not catch up." in paint
    assert "last_rebalance_complete" in paint
    assert "wg-track" in js_text
    assert "util-fill" in js_text
    assert "Allocation " in js_text
    assert "window.confirm" not in js_text


def test_html_keyboard_accelerators(html_text: str) -> None:
    assert 'id="kbd-hint"' in html_text
    assert "Alt+1–5" in html_text or "Alt+1-5" in html_text
    assert "F1 help" in html_text
    assert 'aria-keyshortcuts="Alt+1"' in html_text
    assert 'aria-keyshortcuts="Alt+5"' in html_text
    assert 'aria-keyshortcuts="F1"' in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_alt_digit_and_f1_accelerators(js_text: str) -> None:
    assert "Digit1" in js_text
    assert "Digit5" in js_text
    assert 'ev.key === "F1"' in js_text
    assert "altKey" in js_text
    assert "preventDefault" in js_text
    assert 'ev.key === "1"' not in js_text


def test_js_render_banners_declares_reason_once(js_text: str) -> None:
    block = js_text.split("function renderBanners")[1].split("function renderPortfolio")[0]
    assert block.count("const reason") == 1
    assert "killReason" in block


def test_js_flatten_banner_names_interrupted_flattening(js_text: str) -> None:
    block = js_text.split("function renderBanners")[1].split("function renderPortfolio")[0]
    assert "FLAT: paper account flattened" in block
    assert "flatten_interrupted" in block
    assert "FLAT: interrupted flattening — paper account flattened" in block
    assert block.count("const reason") == 1
    assert "window.confirm" not in js_text


def test_js_activity_flatten_interrupted(js_text: str) -> None:
    flatten_branch = js_text.split('case "flatten":')[1].split("default:")[0]
    assert "flatten_interrupted" in flatten_branch
    assert "interrupted flattening" in flatten_branch


def test_js_flatten_banner_names_limit_breach(js_text: str) -> None:
    block = js_text.split("function renderBanners")[1].split("function renderPortfolio")[0]
    assert "FLAT: limit breach — paper account flattened" in block
    assert 'killReason === "limit"' in block
    assert block.count("const reason") == 1
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text


def test_js_activity_flatten_limit_breach(js_text: str) -> None:
    flatten_branch = js_text.split('case "flatten":')[1].split("default:")[0]
    assert 'ev.reason === "limit"' in flatten_branch
    assert "limit breach" in flatten_branch


def test_js_flatten_banner_names_breached_cap(js_text: str) -> None:
    block = js_text.split("function renderBanners")[1].split("function renderPortfolio")[0]
    assert "policyLabel(killReason)" in block
    assert "NUMERIC_CAPS" in block
    assert "long_only" in block
    assert "FLAT: limit breach — paper account flattened" in block
    assert block.count("const reason") == 1
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text


def test_js_activity_flatten_names_breached_cap(js_text: str) -> None:
    flatten_branch = js_text.split('case "flatten":')[1].split("default:")[0]
    assert "policyLabel(ev.reason)" in flatten_branch
    assert "NUMERIC_CAPS" in flatten_branch
    assert "limit breach" in flatten_branch


def test_html_session_and_cap_mounts(html_text: str) -> None:
    assert 'id="metric-session"' in html_text
    assert 'id="metric-countdown"' in html_text
    assert 'id="metric-countdown-kind"' in html_text
    assert 'id="sleeve-alloc-track"' in html_text
    assert ">Cap<" in html_text
    portfolio_at = html_text.find('id="screen-portfolio"')
    assert html_text.find('id="metric-session"') > portfolio_at


def test_css_focus_visible_and_metric_sub(css_text: str) -> None:
    assert ":focus-visible" in css_text
    assert ".metric-sub" in css_text


def test_js_session_name_and_alloc_rails(js_text: str) -> None:
    assert "function renderSessionMetrics" in js_text
    assert "function nameCapBar" in js_text
    assert "function renderSleeveAllocBook" in js_text
    assert "Spoken " in js_text
    assert "colspan='7'" in js_text
    assert "window.confirm" not in js_text


def test_html_remaining_budget_mounts(html_text: str) -> None:
    assert 'id="metric-names"' in html_text
    assert 'id="metric-names-cap"' in html_text
    assert 'id="metric-names-bar"' in html_text
    assert 'id="metric-orders"' in html_text
    assert 'id="metric-orders-cap"' in html_text
    assert 'id="metric-orders-bar"' in html_text
    assert 'id="metric-cash-bar"' in html_text
    assert 'id="metric-cash-sub"' in html_text
    assert 'id="risk-utilization"' in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_remaining_budget_painters(js_text: str) -> None:
    assert "function renderRemainingBudgets" in js_text
    assert "function renderCashComposition" in js_text
    assert "function paintUtilTrack" in js_text
    assert "window.confirm" not in js_text


def test_html_import_gate_copy(html_text: str) -> None:
    assert 'id="import-error-kind"' in html_text
    assert 'id="import-error-title"' in html_text
    assert 'id="import-error-detail"' in html_text
    assert 'id="import-error-next"' in html_text
    assert 'id="import-ok"' in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_import_gate_painters(js_text: str) -> None:
    assert "function showImportRejection" in js_text
    assert "function showImportOk" in js_text
    assert "Import is not permission to trade" in js_text
    assert "window.confirm" not in js_text


def test_html_desk_pulse_and_activity_heartbeat(html_text: str) -> None:
    assert 'id="desk-pulse"' in html_text
    assert 'id="desk-pulse-label"' in html_text
    assert 'id="activity-heartbeat"' in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_desk_pulse_and_activity_empty(js_text: str) -> None:
    assert "function renderDeskPulse" in js_text
    assert (
        "Heartbeat is running. No audit events yet. Rebalances fire at open+3m and close−12m."
        in js_text
    )
    assert "No audit events yet. Supervisor beat is not live." in js_text
    assert "window.confirm" not in js_text


def test_css_desk_pulse_tokens(css_text: str) -> None:
    assert ".desk-pulse" in css_text
    assert ".pulse-dot" in css_text
    assert "prefers-reduced-motion" in css_text


def test_html_header_session_chips(html_text: str) -> None:
    header = html_text[html_text.find("<header>") : html_text.find("</header>")]
    assert 'id="desk-pulse"' in header
    assert 'id="desk-session"' in header
    assert 'id="desk-supervisor"' in header
    assert "desk-chip" in header
    port = html_text[
        html_text.find('id="screen-portfolio"') : html_text.find('id="screen-strategies"')
    ]
    assert 'id="desk-session"' not in port
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_paints_header_chips(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderDeskPulse") : js_text.find("function renderStrategies")
    ]
    assert "desk-session" in paint
    assert "desk-supervisor" in paint
    assert "function supervisorLabel" in js_text
    assert "function applySessionChip" in js_text
    assert "applySessionChip" in paint
    assert "RTH session" in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_header_chip_tokens(css_text: str) -> None:
    session = re.search(r"#desk-session\.open\s*\{[^}]*\}", css_text)
    halt = re.search(r"#desk-supervisor\.halt\s*\{[^}]*\}", css_text)
    fail = re.search(r"#desk-supervisor\.fail\s*\{[^}]*\}", css_text)
    assert session is not None and "#10b981" in session.group(0).lower()
    assert halt is not None and "#f59e0b" in halt.group(0).lower()
    assert fail is not None and "#ef4444" in fail.group(0).lower()


def test_js_session_chip_warns_when_halted_open(js_text: str) -> None:
    assert "function applySessionChip" in js_text
    body = js_text[
        js_text.find("function applySessionChip") : js_text.find(
            "function renderSessionMetrics"
        )
    ]
    assert "halted" in body
    assert '"warn"' in body
    assert '"open"' in body
    session = js_text[
        js_text.find("function renderSessionMetrics") : js_text.find("function pulseLabel")
    ]
    assert "applySessionChip" in session
    pulse = js_text[
        js_text.find("function renderDeskPulse") : js_text.find("function renderStrategies")
    ]
    assert "applySessionChip" in pulse
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text


def test_css_session_warn_uses_halt_token(css_text: str) -> None:
    desk_warn = re.search(r"#desk-session\.warn\s*\{[^}]*\}", css_text)
    metric_warn = re.search(r"#metric-session\.warn\s*\{[^}]*\}", css_text)
    desk_open = re.search(r"#desk-session\.open\s*\{[^}]*\}", css_text)
    assert desk_warn is not None and "#f59e0b" in desk_warn.group(0).lower()
    assert metric_warn is not None and "#f59e0b" in metric_warn.group(0).lower()
    assert desk_open is not None and "#10b981" in desk_open.group(0).lower()


def test_html_glance_bands(html_text: str) -> None:
    assert 'id="glance-book"' in html_text
    assert 'id="glance-risk"' in html_text
    assert 'id="glance-clock"' in html_text
    assert '<h2 class="glance-heading">Book</h2>' in html_text
    assert '<h2 class="glance-heading">Flatten budgets</h2>' in html_text
    assert '<h2 class="glance-heading">Clock</h2>' in html_text
    book = html_text[html_text.find('id="glance-book"') : html_text.find('id="glance-risk"')]
    risk = html_text[html_text.find('id="glance-risk"') : html_text.find('id="glance-clock"')]
    clock = html_text[html_text.find('id="glance-clock"') : html_text.find('id="glance-positions"')]
    assert 'id="metric-equity"' in book
    assert 'id="metric-cash"' in book
    assert 'id="metric-pnl"' in book
    assert "hero" in book
    assert 'id="metric-gross"' in risk
    assert 'id="metric-names"' in risk
    assert 'id="metric-orders"' in risk
    assert 'id="metric-session"' in clock
    assert 'id="metric-countdown"' in clock
    assert 'id="metric-clock-now"' in clock
    assert 'id="metric-last-rebalance"' in clock
    assert "metrics-4" in clock
    assert "hero" in clock
    assert ">Now<" in clock
    assert ">Last<" in clock
    assert 'id="clock-line"' not in html_text
    assert 'style="margin-top' not in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_css_glance_bands(css_text: str) -> None:
    assert ".glance-band" in css_text
    assert ".glance-heading" in css_text
    assert ".book-grid" in css_text
    assert ".stack" in css_text
    assert "1.85rem" in css_text
    assert ".metrics-3" in css_text
    assert ".metrics-2" in css_text
    assert "repeat(3, minmax(0, 1fr))" in css_text
    assert "repeat(2, minmax(0, 1fr))" in css_text
    assert "max-width: 639px" in css_text
    assert "min-width: 800px" in css_text
    assert ".metric.hero .metric-value" in css_text


def test_html_positions_glance_bands(html_text: str) -> None:
    port = html_text[
        html_text.find('id="screen-portfolio"') : html_text.find('id="screen-strategies"')
    ]
    pos = port[port.find('id="glance-positions"') : port.find('id="glance-sleeves"')]
    sleeves = port[port.find('id="glance-sleeves"') :]
    assert 'id="pos-count-rows"' in pos
    assert 'id="pos-count-wanted"' in pos
    assert 'id="pos-count-got"' in pos
    assert 'id="pos-count-cap"' in pos
    assert "metrics-4" in pos
    assert "hero" in pos
    assert ">Wanted<" in pos
    assert ">At cap<" in pos
    assert 'id="positions-table"' in pos
    assert 'id="sleeves-table"' in sleeves
    assert 'id="sleeve-alloc-track"' in sleeves
    assert "book-grid" in port
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_paints_positions_glance_tiles(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderPositionsGlance") : js_text.find("function renderDeskPulse")
    ]
    assert "pos-count-rows" in paint
    assert "pos-count-wanted" in paint
    assert "pos-count-got" in paint
    assert "pos-count-cap" in paint
    assert "max_name_weight" in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
    assert "Gross cap" not in js_text


def test_css_positions_cap_fail_token(css_text: str) -> None:
    cap = re.search(r"#pos-count-cap\.fail\s*\{[^}]*\}", css_text)
    assert cap is not None and "#ef4444" in cap.group(0).lower()


def test_js_paints_clock_continuity_tiles(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderSessionMetrics") : js_text.find("function renderBookDrift")
    ]
    assert "metric-clock-now" in paint
    assert "metric-last-rebalance" in paint
    assert "last_rebalance_event" in paint
    assert "last_rebalance_complete" in paint
    assert '"spent"' in paint
    assert "warn" in paint
    assert "clock-line" not in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_last_rebalance_spent_warn_token(css_text: str) -> None:
    last = re.search(r"#metric-last-rebalance\.warn\s*\{[^}]*\}", css_text)
    assert last is not None and "#f59e0b" in last.group(0).lower()


def test_js_uses_api_policy_labels(js_text: str) -> None:
    assert "function policyLabel" in js_text
    assert "risk.labels" in js_text
    assert "Gross cap" not in js_text
    assert "${policyLabel(key)} cannot loosen" in js_text
    assert "${key} cannot loosen" not in js_text
    assert "window.confirm" not in js_text


def test_html_screen_help_howto(html_text: str) -> None:
    assert 'id="help-howto"' in html_text
    assert 'id="help-runbook"' in html_text
    assert "Full runbook" in html_text
    assert 'id="help-body"' in html_text
    assert 'data-screen="help"' not in html_text
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_renders_howto_for_active_screen(js_text: str) -> None:
    assert 'getElementById("help-howto")' in js_text
    assert "payload.howtos" in js_text
    assert "function activeScreen" in js_text
    assert "item.screen === screen" in js_text
    show = js_text[js_text.find("function showScreen") : js_text.find("function setError")]
    assert "renderHelp" in show
    load = js_text[js_text.find("async function loadHelp") : js_text.find("function setHelpOpen")]
    assert 'getElementById("help-howto")' in load
    assert "Help unavailable" in load
    assert "window.confirm" not in js_text


def test_html_run_kill_switch_zones(html_text: str) -> None:
    assert 'id="run-promote"' in html_text
    assert 'id="run-book"' in html_text
    assert 'id="run-recover"' in html_text
    assert 'id="run-flatten"' in html_text
    assert '<h2 class="glance-heading">Start paper</h2>' in html_text
    assert '<h2 class="glance-heading">Sleeves</h2>' in html_text
    assert '<h2 class="glance-heading">After halt</h2>' in html_text
    assert '<h2 class="glance-heading">Flatten account</h2>' in html_text
    run = html_text[html_text.find('id="screen-run"') : html_text.find('id="screen-activity"')]
    promote = run[run.find('id="run-promote"') : run.find('id="run-book"')]
    book = run[run.find('id="run-book"') : run.find('id="run-recover"')]
    recover = run[run.find('id="run-recover"') : run.find('id="run-flatten"')]
    flatten = run[run.find('id="run-flatten"') :]
    assert 'id="start-form"' in promote
    assert 'id="run-error"' in promote
    assert 'id="run-sleeves"' in book
    assert 'id="run-remaining"' in book
    assert 'id="run-spoken"' in book
    assert 'id="run-count-active"' in book
    assert 'id="run-count-idle"' in book
    assert "metrics-4" in book
    assert "hero" in book
    assert ">Remaining<" in book
    assert 'id="account-resume"' in recover
    assert 'id="run-halt-reason"' in recover
    assert 'id="run-halt-reason"' not in flatten
    assert 'id="account-kill"' not in recover
    assert 'id="account-kill"' in flatten
    assert 'id="account-kill-phrase"' in flatten
    assert 'id="account-kill-confirm"' in flatten
    assert 'id="account-resume"' not in flatten
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_css_run_kill_switch_zones(css_text: str) -> None:
    assert ".flatten-zone" in css_text
    assert ".recover-zone" in css_text
    assert ".flatten-zone .panel" in css_text
    assert ".flatten-zone .glance-heading" in css_text


def test_js_paints_run_capacity(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRunSleeves") : js_text.find("function eventSummary")
    ]
    assert "run-remaining" in paint
    assert "run-spoken" in paint
    assert "run-count-active" in paint
    assert "run-count-idle" in paint
    assert "No sleeves yet" in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_paints_run_halt_reason(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRunRecover") : js_text.find("function eventSummary")
    ]
    assert "run-halt-reason" in paint
    assert "halt_reason" in paint
    assert "Resume is only after halt." in paint
    assert "innerHTML" not in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_run_remaining_tokens(css_text: str) -> None:
    warn = re.search(r"#run-remaining\.warn\s*\{[^}]*\}", css_text)
    fail = re.search(r"#run-remaining\.fail\s*\{[^}]*\}", css_text)
    assert warn is not None and "#f59e0b" in warn.group(0).lower()
    assert fail is not None and "#ef4444" in fail.group(0).lower()


def test_html_run_band_errors(html_text: str) -> None:
    run = html_text[html_text.find('id="screen-run"') : html_text.find('id="screen-activity"')]
    promote = run[run.find('id="run-promote"') : run.find('id="run-book"')]
    book = run[run.find('id="run-book"') : run.find('id="run-recover"')]
    recover = run[run.find('id="run-recover"') : run.find('id="run-flatten"')]
    flatten = run[run.find('id="run-flatten"') :]
    assert 'id="run-error"' in promote
    assert 'id="run-sleeve-error"' in book
    assert 'id="run-recover-error"' in recover
    assert 'id="run-flatten-error"' in flatten
    assert 'id="run-flatten-error"' not in promote
    assert 'id="run-error"' not in flatten
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_set_run_error_by_band(js_text: str) -> None:
    assert "function setRunError" in js_text
    kill = js_text[
        js_text.find('getElementById("account-kill")') : js_text.find(
            'getElementById("account-resume")'
        )
    ]
    assert 'setRunError("flatten"' in kill
    resume = js_text[
        js_text.find('getElementById("account-resume")') : js_text.find("function activeScreen")
    ]
    assert 'setRunError("recover"' in resume
    assert 'setRunError("sleeves"' in js_text
    assert 'setRunError("promote"' in js_text
    assert "window.confirm" not in js_text


def test_cockpit_js_assembled_from_parts() -> None:
    from alphastrategy.web.cockpit import JS_PARTS, STATIC_DIR, cockpit_js

    assert JS_PARTS == (
        "js/core.js",
        "js/paint-rails.js",
        "js/paint-portfolio.js",
        "js/paint-strategies.js",
        "js/paint-run.js",
        "js/paint-activity.js",
        "js/paint-risk.js",
        "js/boot.js",
    )
    for rel in JS_PARTS:
        path = STATIC_DIR / rel
        assert path.is_file(), rel
        nlines = path.read_text(encoding="utf-8").count("\n")
        assert nlines <= 400, f"{rel} has {nlines} newlines"
    assert not (STATIC_DIR / "app.js").is_file()
    blob = cockpit_js()
    assert blob.startswith("(function () {")
    assert blob.rstrip().endswith("})();")
    assert "function setRunError" in blob
    assert "function renderPortfolio" in blob
    assert "window.confirm" not in blob
    assert "window.state" not in blob
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert '<script src="app.js"></script>' in html


def test_cockpit_js_includes_paint_rails() -> None:
    from alphastrategy.web.cockpit import JS_PARTS, STATIC_DIR, cockpit_js

    assert JS_PARTS[0] == "js/core.js"
    assert JS_PARTS[1] == "js/paint-rails.js"
    assert JS_PARTS[2] == "js/paint-portfolio.js"
    rails = (STATIC_DIR / "js/paint-rails.js").read_text(encoding="utf-8")
    port = (STATIC_DIR / "js/paint-portfolio.js").read_text(encoding="utf-8")
    assert "function renderRiskUtilization" in rails
    assert "function wantedGotBar" in rails
    assert "function renderRiskUtilization" not in port
    assert "function renderPortfolio" in port
    assert "function renderFirstRun" in port
    assert rails.count("\n") <= 400
    assert "window.state" not in cockpit_js()


def test_html_strategies_inventory_bands(html_text: str) -> None:
    assert 'id="strat-inventory"' in html_text
    assert 'id="strat-import"' in html_text
    assert 'id="strat-roster"' in html_text
    assert '<h2 class="glance-heading">Inventory</h2>' in html_text
    assert '<h2 class="glance-heading">Import .asb</h2>' in html_text
    assert '<h2 class="glance-heading">Roster</h2>' in html_text
    strat = html_text[
        html_text.find('id="screen-strategies"') : html_text.find('id="screen-run"')
    ]
    inventory = strat[strat.find('id="strat-inventory"') : strat.find('id="strat-import"')]
    bring = strat[strat.find('id="strat-import"') : strat.find('id="strat-roster"')]
    roster = strat[strat.find('id="strat-roster"') :]
    assert 'id="strat-count-imported"' in inventory
    assert 'id="strat-count-paper"' in inventory
    assert 'id="strat-count-halted"' in inventory
    assert 'id="strat-count-stopped"' in inventory
    assert "hero" in inventory
    assert 'id="import-form"' in bring
    assert 'id="import-error"' in bring
    assert 'id="import-ok"' in bring
    assert 'id="strategies-table"' in roster
    assert 'id="import-form"' not in roster
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_css_strategies_inventory_bands(css_text: str) -> None:
    assert ".metrics-4" in css_text
    assert "repeat(4, minmax(0, 1fr))" in css_text


def test_js_paints_strategy_inventory(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderStrategies") : js_text.find("function runFormIsDirty")
    ]
    assert '"strat-count-paper"' in paint
    assert '"strat-count-imported"' in paint
    assert '"strat-count-halted"' in paint
    assert '"strat-count-stopped"' in paint
    assert '"status-running"' in paint
    assert '"status-halt"' in paint
    assert '"status-stopped"' in paint
    assert "classList.toggle(onClass" in paint
    assert "imported_at" in paint
    assert "slice(0, 10)" in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_html_risk_glance_bands(html_text: str) -> None:
    assert 'id="risk-caps"' in html_text
    assert 'id="risk-headroom"' in html_text
    assert 'id="risk-tighten"' in html_text
    assert 'id="risk-overlays"' in html_text
    assert '<h2 class="glance-heading">Caps</h2>' in html_text
    assert '<h2 class="glance-heading">Headroom</h2>' in html_text
    assert '<h2 class="glance-heading">Tighten</h2>' in html_text
    assert '<h2 class="glance-heading">Sleeve overlays</h2>' in html_text
    risk = html_text[html_text.find('id="screen-risk"') :]
    caps = risk[risk.find('id="risk-caps"') : risk.find('id="risk-headroom"')]
    head = risk[risk.find('id="risk-headroom"') : risk.find('id="risk-tighten"')]
    tighten = risk[risk.find('id="risk-tighten"') : risk.find('id="risk-overlays"')]
    overlays = risk[risk.find('id="risk-overlays"') :]
    assert 'id="risk-account-caps"' in caps
    assert 'id="risk-cap-gross"' in caps
    assert 'id="risk-cap-name"' in caps
    assert 'id="risk-cap-names"' in caps
    assert 'id="risk-cap-orders"' in caps
    assert 'id="risk-cap-long"' in caps
    assert "metrics-4" in caps
    assert "hero" in caps
    assert ">Gross cap<" in caps
    assert ">Name cap<" in caps
    assert 'id="risk-utilization"' in head
    assert 'id="risk-head-names"' in head
    assert 'id="risk-head-orders"' in head
    assert 'id="risk-head-cash"' in head
    assert 'id="risk-head-target"' in head
    assert "metrics-4" in head
    assert "hero" in head
    assert ">Names<" in head
    assert ">Target cash<" in head
    assert 'id="risk-account-form"' in tighten
    assert 'id="risk-error"' in tighten
    assert 'id="risk-tighten-tight"' in tighten
    assert 'id="risk-tighten-delta-dollar"' in tighten
    assert 'id="risk-tighten-delta-frac"' in tighten
    assert 'id="risk-tighten-fields"' in tighten
    assert "metrics-4" in tighten
    assert "hero" in tighten
    assert ">Tight<" in tighten
    assert ">Delta $<" in tighten
    assert ">Delta %<" in tighten
    assert ">Fields<" in tighten
    assert 'id="risk-sleeves"' in overlays
    assert 'id="risk-overlay-spoken"' in overlays
    assert 'id="risk-overlay-count"' in overlays
    assert 'id="risk-overlay-tighter"' in overlays
    assert 'id="risk-overlay-idle"' in overlays
    assert "metrics-4" in overlays
    assert "hero" in overlays
    assert ">Spoken<" in overlays
    assert 'id="risk-account-form"' not in overlays
    sticky = html_text[
        html_text.find("risk-account-bar") : html_text.find('id="risk-tighten"')
    ]
    assert 'id="risk-caps"' in sticky
    assert 'id="risk-headroom"' in sticky
    assert 'id="risk-account-form"' not in sticky
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_css_risk_tighten_groups(css_text: str) -> None:
    assert ".risk-tighten-groups" in css_text
    assert ".risk-group" in css_text


def test_js_paints_risk_overlay_glance(js_text: str) -> None:
    paint = js_text[js_text.find("function overlayTighterCount") :]
    assert "function overlayTighterCount" in js_text
    assert "risk-overlay-spoken" in paint
    assert "risk-overlay-count" in paint
    assert "risk-overlay-tighter" in paint
    assert "risk-overlay-idle" in paint
    assert "paintUtilTrack" in paint
    assert "No sleeve overlays" in paint
    assert "tighter than account" in paint
    assert "tighter-line" in paint
    assert "risk-sleeve-tighten" in paint
    assert "Tighten this sleeve" in paint
    assert 'createElement("details")' in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_risk_form_dirty_includes_open_details(js_text: str) -> None:
    fn = js_text.split("function riskFormIsDirty")[1].split("function renderRisk")[0]
    assert "details[open]" in fn
    assert "#screen-risk" in fn
    risk_fn = js_text[js_text.find("function renderRisk") :]
    glance = risk_fn.find("renderTightenGlance")
    overlay = risk_fn.find("renderOverlayGlance")
    dirty = risk_fn.find("if (riskFormIsDirty())")
    assert glance != -1 and overlay != -1 and dirty != -1
    assert glance < dirty and overlay < dirty
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_paints_risk_tighten_glance(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderTightenGlance") : js_text.find(
            "function renderOverlayGlance"
        )
    ]
    assert "function renderTightenGlance" in js_text
    assert "risk-tighten-tight" in paint
    assert "risk-tighten-delta-dollar" in paint
    assert "risk-tighten-delta-frac" in paint
    assert "risk-tighten-fields" in paint
    assert "overlayTighterCount" in paint
    assert "min_delta_dollar" in paint
    assert "min_delta_frac" in paint
    assert "NUMERIC_CAPS.length" in paint
    assert "fmtNum" in paint
    assert "fmtPct" in paint
    risk_fn = js_text[js_text.find("function renderRisk") :]
    glance = risk_fn.find("renderTightenGlance")
    dirty = risk_fn.find("if (riskFormIsDirty())")
    assert glance != -1 and dirty != -1 and glance < dirty
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_risk_tighten_tokens(css_text: str) -> None:
    tight = re.search(r"#risk-tighten-tight\.warn\s*\{[^}]*\}", css_text)
    assert tight is not None and "#f59e0b" in tight.group(0).lower()


def test_css_risk_overlay_tokens(css_text: str) -> None:
    warn = re.search(r"#risk-overlay-spoken\.warn\s*\{[^}]*\}", css_text)
    fail = re.search(r"#risk-overlay-spoken\.fail\s*\{[^}]*\}", css_text)
    tight = re.search(r"#risk-overlay-tighter\.warn\s*\{[^}]*\}", css_text)
    assert warn is not None and "#f59e0b" in warn.group(0).lower()
    assert fail is not None and "#ef4444" in fail.group(0).lower()
    assert tight is not None and "#f59e0b" in tight.group(0).lower()


def test_css_risk_overlay_card_tokens(css_text: str) -> None:
    tight = re.search(
        r"#risk-sleeves\s+\.tighter-line\.warn\s*\{[^}]*\}", css_text
    )
    summary = re.search(r"\.risk-sleeve-tighten\s+summary\s*\{[^}]*\}", css_text)
    assert tight is not None and "#f59e0b" in tight.group(0).lower()
    assert summary is not None and "#9ba3b4" in summary.group(0).lower()


def test_js_paints_risk_caps_tiles(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRiskCaps") : js_text.find("function buildRiskInputs")
    ]
    assert "risk-cap-gross" in paint
    assert "risk-cap-name" in paint
    assert "risk-cap-names" in paint
    assert "risk-cap-orders" in paint
    assert "risk-cap-long" in paint
    assert "max_gross" in paint
    assert "max_name_weight" in paint
    assert "max_orders_per_day" in paint
    assert "fmtPct" in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_paints_risk_headroom_tiles(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRiskUtilization") : js_text.find("function nameCapBar")
    ]
    assert "risk-head-names" in paint
    assert "risk-head-orders" in paint
    assert "risk-head-cash" in paint
    assert "risk-head-target" in paint
    assert "target_cash_weight" in paint
    assert "paintUtilTrack" in paint
    assert 'innerHTML = ""' not in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_risk_headroom_fail_tokens(css_text: str) -> None:
    names = re.search(r"#risk-head-names\.fail\s*\{[^}]*\}", css_text)
    orders = re.search(r"#risk-head-orders\.fail\s*\{[^}]*\}", css_text)
    assert names is not None and "#ef4444" in names.group(0).lower()
    assert orders is not None and "#ef4444" in orders.group(0).lower()


def test_js_risk_tighten_groups(js_text: str) -> None:
    paint = js_text[
        js_text.find("RISK_TIGHTEN_GROUPS") : js_text.find("function renderRiskCaps")
    ]
    assert 'legend: "Gross"' in paint
    assert 'legend: "Names"' in paint
    assert 'legend: "Orders"' in paint
    assert 'legend: "Deltas"' in paint
    assert '"max_gross"' in paint
    assert '"max_names"' in paint
    assert '"max_orders_per_day"' in paint
    assert '"min_delta_dollar"' in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text
    built = js_text[
        js_text.find("function buildRiskInputs") : js_text.find("function validateTighten")
    ]
    assert 'createElement("fieldset")' in built


def test_html_activity_tape_bands(html_text: str) -> None:
    assert 'id="act-beat"' in html_text
    assert 'id="act-tape"' in html_text
    assert 'id="act-blotter"' in html_text
    assert '<h2 class="glance-heading">Beat</h2>' in html_text
    assert '<h2 class="glance-heading">Tape</h2>' in html_text
    assert '<h2 class="glance-heading">Blotter</h2>' in html_text
    act = html_text[
        html_text.find('id="screen-activity"') : html_text.find('id="screen-risk"')
    ]
    beat = act[act.find('id="act-beat"') : act.find('id="act-tape"')]
    tape = act[act.find('id="act-tape"') : act.find('id="act-blotter"')]
    blotter = act[act.find('id="act-blotter"') :]
    assert 'id="activity-heartbeat"' in beat
    assert 'id="act-beat-age"' in beat
    assert 'id="act-beat-interval"' in beat
    assert 'id="act-beat-state"' in beat
    assert "metrics-4" in beat
    assert "hero" in beat
    assert ">Pulse<" in beat
    assert 'id="act-count-rebalance"' in tape
    assert 'id="act-count-spent"' in tape
    assert ">Rebalances<" in tape
    assert 'id="act-count-halt"' in tape
    assert 'id="act-count-deviation"' in tape
    assert 'id="act-count-kill"' in tape
    assert "hero" in tape
    assert 'id="activity-list"' in blotter
    assert 'id="activity-list"' not in tape
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]


def test_js_paints_activity_tape(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderActivity") : js_text.find("RISK_TIGHTEN_GROUPS")
    ]
    assert '"act-count-rebalance"' in paint
    assert '"act-count-spent"' in paint
    assert '"act-count-halt"' in paint
    assert '"act-count-deviation"' in paint
    assert '"act-count-kill"' in paint
    assert '"status-running"' in paint
    assert '"status-halt"' in paint
    assert '"status-fail"' in paint
    assert 'event === "rebalance"' in paint
    assert 'event === "execution_deviation"' in paint
    assert 'event === "flatten"' in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_activity_spent_rebalance(js_text: str) -> None:
    summary = js_text[
        js_text.find("function eventSummary") : js_text.find("function renderActivity")
    ]
    paint = js_text[
        js_text.find("function renderActivity") : js_text.find("RISK_TIGHTEN_GROUPS")
    ]
    assert "complete === false" in summary
    assert "spent" in summary
    assert "incomplete" not in summary
    assert '["Spent"' in summary or '"Spent"' in summary
    assert "act-count-spent" in paint
    assert "warn" in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_rebalance_spent_warn_token(css_text: str) -> None:
    reb = re.search(r"#act-count-rebalance\.warn\s*\{[^}]*\}", css_text)
    assert reb is not None and "#f59e0b" in reb.group(0).lower()


def test_js_deviation_banner_follows_book_drift(js_text: str) -> None:
    boot = js_text[
        js_text.find("function detectDeviation") : js_text.find("async function refresh")
    ]
    assert "bookDrift" in boot
    assert "last_rebalance_complete" in boot
    assert "last_combined" in boot
    assert 'ev.event === "resume"' not in boot
    assert "function bookDrift" in js_text
    banners = js_text[
        js_text.find("function renderBanners") : js_text.find("function renderPortfolio")
    ]
    assert "deviationActive" in banners
    assert "DEVIATION: execution drift exceeds tolerance" in banners
    assert banners.count("const reason") == 1
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_paints_activity_beat(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderActivity") : js_text.find("RISK_TIGHTEN_GROUPS")
    ]
    assert "function supervisorLabel" in js_text
    assert "act-beat-age" in paint
    assert "act-beat-interval" in paint
    assert "act-beat-state" in paint
    assert "interval_seconds" in paint
    assert "IN SESSION" in js_text
    assert "window.confirm" not in js_text


def test_css_activity_beat_pulse_tokens(css_text: str) -> None:
    live = re.search(r"#activity-heartbeat\.live\s*\{[^}]*\}", css_text)
    stale = re.search(r"#activity-heartbeat\.stale\s*\{[^}]*\}", css_text)
    dead = re.search(r"#activity-heartbeat\.dead\s*\{[^}]*\}", css_text)
    assert live is not None and "#10b981" in live.group(0).lower()
    assert stale is not None and "#f59e0b" in stale.group(0).lower()
    assert dead is not None and "#ef4444" in dead.group(0).lower()


def test_js_activity_drill_in_is_book_not_json(js_text: str) -> None:
    paint = js_text[
        js_text.find("function eventSummary") : js_text.find("RISK_TIGHTEN_GROUPS")
    ]
    assert "function bookTable" in paint
    assert "function eventDetail" in paint
    assert "activity-book" in paint
    assert "activity-fields" in paint
    assert "<th>Wanted</th>" in paint
    assert "<th>Got</th>" in paint
    assert "JSON.stringify(payload" not in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_activity_book_drill_in(css_text: str) -> None:
    assert ".activity-book" in css_text
    assert ".activity-fields" in css_text
    detail = re.search(r"\.activity-detail\s*\{[^}]*\}", css_text, re.DOTALL)
    assert detail is not None
    assert "pre-wrap" not in detail.group(0)


def test_html_help_tasks(html_text: str) -> None:
    assert 'id="help-tasks"' in html_text
    assert 'id="help-howto"' in html_text
    assert 'id="help-tutorial"' in html_text
    assert html_text.find('id="help-tutorial"') < html_text.find('id="help-howto"')
    nav = re.search(r'<nav id="nav"[^>]*>(.*?)</nav>', html_text, re.DOTALL)
    screens = re.findall(r'data-screen="([^"]+)"', nav.group(1))
    assert screens == ["portfolio", "strategies", "run", "activity", "risk"]
    assert "help" not in screens


def test_js_renders_help_tasks(js_text: str) -> None:
    paint = js_text[js_text.find("function renderHelp") : js_text.find("async function loadHelp")]
    assert "payload.tasks" in paint
    assert 'getElementById("help-tasks")' in paint
    assert "item.screens" in paint
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_renders_help_tutorial(js_text: str) -> None:
    paint = js_text[js_text.find("function renderHelp") : js_text.find("async function loadHelp")]
    assert "payload.tutorials" in paint
    assert 'getElementById("help-tutorial")' in paint
    assert "window.confirm" not in js_text


def test_css_help_tutorial_uses_running_token(css_text: str) -> None:
    block = re.search(r"#help-tutorial h3\s*\{[^}]*\}", css_text)
    assert block is not None
    assert "#10b981" in block.group(0).lower()
