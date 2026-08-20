# Caps Live-Limit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Caps tiles fail on the spoken cap `live_limit` names; CLI `status` writes the LIMIT sentence to stderr without breaking JSON stdout.

**Architecture:** Paint-only on Caps (reuse `utilization.live_limit`). CLI maps `label_for(reason)` after the existing status payload. No engine flatten.

**Tech Stack:** Quiet cockpit JS/CSS, CLI, helptext, README, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-caps-limit-requirements.md`](../requirements/2026-08-20-alphastrategy-caps-limit-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. GET status/risk must not flatten.
- CLI `status` stdout stays JSON.
- Each `js/` part stays ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/paint-risk.js`, `src/alphastrategy/web/static/styles.css`, `src/alphastrategy/cli/main.py`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_cli.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add:

```python
    "Caps names the cap the live book is through",
    "status names LIMIT while the live book is through the spoken cap",
```

In `tests/alphastrategy/test_web_tokens.py` after `test_css_risk_cap_spoken_warn_token`:

```python
def test_js_paints_risk_caps_live_limit(js_text: str) -> None:
    paint = js_text[
        js_text.find("function renderRiskCaps") : js_text.find("function buildRiskInputs")
    ]
    assert "live_limit" in paint
    assert 'classList.add("fail")' in paint
    assert "max_name_weight" in paint
    assert "long_only" in paint
    assert "warn" in paint
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_css_risk_cap_live_limit_fail_token(css_text: str) -> None:
    for sel in (
        "#risk-cap-gross.fail",
        "#risk-cap-name.fail",
        "#risk-cap-names.fail",
        "#risk-cap-orders.fail",
        "#risk-cap-long.fail",
    ):
        block = re.search(re.escape(sel) + r"\s*\{[^}]*\}", css_text)
        assert block is not None and "#ef4444" in block.group(0).lower()
```

In `tests/alphastrategy/test_cli.py` after `test_status_prints_json`:

```python
def test_status_prints_limit_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    from alphastrategy.supervisor.state import load_state, save_state

    _create_imported_bundle(cli_home)
    main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"])
    home = AlphaStrategyHome.from_env()
    snap = load_state(home.state_path())
    snap.last_got = {"AAPL": 0.225}
    save_state(home.state_path(), snap)
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert payload["utilization"]["live_limit"]["reason"] == "max_name_weight"
    err = captured.err
    assert "LIMIT:" in err
    assert "Name cap" in err
    assert "next rebalance will flatten" in err.lower()
    patch_alpaca.assert_not_called()


def test_status_omits_limit_when_flattened(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    from alphastrategy.supervisor.state import load_state, save_state

    _create_imported_bundle(cli_home)
    main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"])
    home = AlphaStrategyHome.from_env()
    snap = load_state(home.state_path())
    snap.last_got = {"AAPL": 0.225}
    snap.state = SupervisorState.STOPPED
    save_state(home.state_path(), snap)
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    json.loads(captured.out.strip())
    assert "LIMIT:" not in captured.err
    patch_alpaca.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_web_tokens.py::test_js_paints_risk_caps_live_limit \
  tests/alphastrategy/test_web_tokens.py::test_css_risk_cap_live_limit_fail_token \
  tests/alphastrategy/test_cli.py::test_status_prints_limit_on_stderr \
  tests/alphastrategy/test_cli.py::test_status_omits_limit_when_flattened \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL. Caps paint lacks `live_limit` fail. CSS lacks `.fail`. CLI stderr lacks LIMIT. Help phrases missing.

If `test_status_prints_json` still passes after GREEN, keep stdout JSON-only.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-caps-limit-requirements.md \
  docs/plans/2026-08-20-alphastrategy-caps-limit-technical-design.md \
  tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_cli.py \
  tests/alphastrategy/test_helptext.py
git commit -m "test: Caps fail on live_limit; status names LIMIT"
```

---

### Task 2: Paint + CLI + help

- [ ] **Step 1: Caps fail from live_limit**

In `renderRiskCaps`, after `markTighter` calls:

```javascript
    const flattened =
      Boolean(state.status && state.status.flattened) ||
      (state.status &&
        (state.status.state === "stopped" || state.status.state === "flattening"));
    function markLimit(el, key) {
      if (!el) return;
      el.classList.remove("fail");
      if (flattened) return;
      const limit = utilization().live_limit;
      if (limit && limit.reason === key) el.classList.add("fail");
    }
    markLimit(gross, "max_gross");
    markLimit(name, "max_name_weight");
    markLimit(names, "max_names");
    markLimit(orders, "max_orders_per_day");
    markLimit(longEl, "long_only");
```

CSS after the existing Caps `.warn` rules, **separate selectors** (do not combine):

```css
#risk-cap-gross.fail {
  color: #ef4444;
}

#risk-cap-name.fail {
  color: #ef4444;
}

#risk-cap-names.fail {
  color: #ef4444;
}

#risk-cap-orders.fail {
  color: #ef4444;
}

#risk-cap-long.fail {
  color: #ef4444;
}
```

- [ ] **Step 2: CLI status stderr**

```python
from alphastrategy.risk.labels import label_for

_LIMIT_STATUS = (
    "LIMIT: live book through {label} — next rebalance will flatten"
)

def _status_limit_line(payload: dict[str, Any]) -> str | None:
    if payload.get("flattened"):
        return None
    util = payload.get("utilization") if isinstance(payload.get("utilization"), dict) else {}
    limit = util.get("live_limit") if isinstance(util, dict) else None
    if not isinstance(limit, dict):
        return None
    reason = limit.get("reason")
    if not reason:
        return None
    return _LIMIT_STATUS.format(label=label_for(str(reason)))
```

In `_cmd_status`, after a successful JSON print (both control-plane and offline branches):

```python
        print(json.dumps(payload, separators=(",", ":")))
        line = _status_limit_line(payload)
        if line:
            print(line, file=sys.stderr)
        return 0
```

- [ ] **Step 3: Help / README**

`how_risk` after Caps is the spoken book: `Caps names the cap the live book is through.`

`cli` section: `status names LIMIT while the live book is through the spoken cap.`

README Caps line: Caps names the cap the live book is through. Status bullet: status names LIMIT while the live book is through the spoken cap.

- [ ] **Step 4: Targeted tests then full suite**

Expected: PASS. JS parts ≤ 400 lines. `test_status_prints_json` still parses stdout.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: Caps fail on live_limit; status names LIMIT"
```
