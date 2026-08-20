# Live Spoken-Cap Warning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When marked live weights already breach the spoken flatten book, utilization names `live_limit` and the desk shows a warn banner that the next rebalance will flatten; spoken cap 0 paints as 0.

**Architecture:** `summarize` runs read-only `check_book` on `last_got`. Cockpit `#live-limit-banner` consumes `utilization.live_limit`. Glance caps use `Number.isFinite` so 0 is a real limit.

**Tech Stack:** utilization, local HTTP API, Quiet cockpit HTML/JS/CSS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-live-limit-requirements.md`](../requirements/2026-08-20-alphastrategy-live-limit-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Heartbeat does not flatten. GET status/risk must not flatten.
- Each `js/` part stays ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/risk/utilization.py`, `src/alphastrategy/web/static/index.html`, `src/alphastrategy/web/static/js/paint-rails.js`, `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`REQUIRED_PHRASES` add `"A live book through the spoken cap warns before the next rebalance flattens"`.

In `tests/alphastrategy/test_risk.py` after `test_from_supervisor_uses_spoken_policy`:

```python
def test_summarize_live_limit_from_marked_name() -> None:
    out = summarize(
        policy=AccountPolicy.defaults(),
        orders_today=0,
        last_got={"AAPL": 0.225},
    )
    assert out["live_limit"]["reason"] == "max_name_weight"


def test_summarize_live_limit_none_inside_cap() -> None:
    out = summarize(
        policy=AccountPolicy.defaults(),
        orders_today=0,
        last_got={"AAPL": 0.15},
    )
    assert out["live_limit"] is None


def test_summarize_live_limit_zero_name_cap() -> None:
    out = summarize(
        policy=replace(AccountPolicy.defaults(), max_name_weight=0.0),
        orders_today=0,
        last_got={"AAPL": 0.15},
    )
    assert out["live_limit"]["reason"] == "max_name_weight"


def test_merge_limits_overlay_zero_name_cap() -> None:
    merged = merge_limits({}, AccountPolicy.defaults(), {"max_name_weight": 0})
    assert merged.max_name_weight == 0.0
```

If `test_merge_limits_overlay_zero_name_cap` PASSES on RED, keep it as a lock.

In `tests/alphastrategy/test_api.py` after `test_get_risk_spoken_follows_allocated_overlay` (or near other GET status tests):

```python
def test_status_live_limit_does_not_flatten(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {"AAPL": 0.225}
    supervisor.snapshot.last_prices = {"AAPL": 150.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 15.0}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "max_name_weight"
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["live_limit"]["reason"] == "max_name_weight"
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"
```

In `test_html_desk_banners_outside_portfolio` add `"live-limit-banner"` to the banner id tuple.

In `tests/alphastrategy/test_web_tokens.py`:

```python
def test_js_paints_live_limit_banner(js_text: str) -> None:
    banners = js_text[
        js_text.find("function renderBanners") : js_text.find("function renderPortfolio")
    ]
    assert "live-limit-banner" in js_text
    assert "live_limit" in js_text
    assert "next rebalance will flatten" in js_text
    assert banners.count("const reason") == 1
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    assert "window.state" not in js_text


def test_js_spoken_caps_treat_zero_as_a_limit(js_text: str) -> None:
    rails = js_text[
        js_text.find("function wantedGotBar") : js_text.find("function renderSleeveAllocBook")
    ]
    assert "Number.isFinite" in rails
    port = js_text[
        js_text.find("function renderPortfolio") : js_text.find("function pulseLabel")
    ]
    assert "spokenNameCap" in js_text or "Number.isFinite" in port
    assert "Gross cap" not in js_text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src python3 -m pytest \
  tests/alphastrategy/test_risk.py::test_summarize_live_limit_from_marked_name \
  tests/alphastrategy/test_risk.py::test_summarize_live_limit_none_inside_cap \
  tests/alphastrategy/test_risk.py::test_summarize_live_limit_zero_name_cap \
  tests/alphastrategy/test_risk.py::test_merge_limits_overlay_zero_name_cap \
  tests/alphastrategy/test_api.py::test_status_live_limit_does_not_flatten \
  tests/alphastrategy/test_web_tokens.py::test_html_desk_banners_outside_portfolio \
  tests/alphastrategy/test_web_tokens.py::test_js_paints_live_limit_banner \
  tests/alphastrategy/test_web_tokens.py::test_js_spoken_caps_treat_zero_as_a_limit \
  tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q
```

Expected: FAIL on missing `live_limit`, missing banner, `Number.isFinite` absent, help phrase missing. Overlay 0 may already PASS.

- [ ] **Step 3: Commit failing tests + docs**

```bash
git add docs/requirements/2026-08-20-alphastrategy-live-limit-requirements.md \
  docs/plans/2026-08-20-alphastrategy-live-limit-technical-design.md \
  tests/alphastrategy/test_risk.py tests/alphastrategy/test_api.py \
  tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_helptext.py
git commit -m "test: live spoken-cap breach warns; zero cap is a real limit"
```

---

### Task 2: Engine, banner, finite caps, help

- [ ] **Step 1: `live_limit` on summarize**

In `utilization.py` import `FlattenRequested` and `check_book`. In `summarize` after building the dict keys, set:

```python
    live_limit = None
    if last_got:
        try:
            check_book(dict(last_got), 0.0, policy)
        except FlattenRequested as exc:
            live_limit = {"reason": str(exc.reason or "limit")}
```

Include `"live_limit": live_limit` in the returned dict.

- [ ] **Step 2: HTML banner**

In `index.html` `#desk-banners` after `#flatten-banner`:

```html
        <div id="live-limit-banner" class="banner halt hidden" role="alert"></div>
```

- [ ] **Step 3: JS rails + banners**

In `paint-rails.js` add:

```javascript
  function finiteNumber(value, fallback) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function spokenNameCap() {
    const spoken = spokenPolicy();
    const util = utilization();
    if (Number.isFinite(Number(spoken.max_name_weight))) {
      return Number(spoken.max_name_weight);
    }
    if (Number.isFinite(Number(util.max_name_weight))) {
      return Number(util.max_name_weight);
    }
    return 0.2;
  }

  function renderLiveLimitBanner(flattened) {
    const el = document.getElementById("live-limit-banner");
    if (!el) return;
    const limit = utilization().live_limit;
    if (flattened || !limit || !limit.reason) {
      el.classList.add("hidden");
      el.textContent = "";
      return;
    }
    el.classList.remove("hidden");
    el.textContent =
      "LIMIT: live book through " +
      policyLabel(limit.reason) +
      " — next rebalance will flatten";
  }
```

`wantedGotBar`: `const capN = finiteNumber(cap, 0.2); const scale = Math.max(capN, w, g, 0.01);`

`paintUtilTrack`: if `Number.isFinite(limit) && limit === 0`, fail when `used > 0`, fill 100% when used > 0.

`renderGrossUtilization`: `const limit = finiteNumber(util.max_gross, finiteNumber(spoken.max_gross, 1));` — do not coerce 0 to 1.

`nameCapBar`: `const limit = finiteNumber(cap, 0.2);` if limit === 0, fail when got > 0.

`fillUsedCap` atCap: `Number.isFinite(Number(cap)) && Number(used) > Number(cap)`.

In `renderBanners` after flatten block, `renderLiveLimitBanner(flattened);` — do not add another `const reason`.

Positions table and glance: `const cap = spokenNameCap();` At cap count: `Number.isFinite(cap) && Math.abs(Number(pos.weight) || 0) > cap`.

- [ ] **Step 4: Help / README**

how_portfolio / halt_flatten / README: `A live book through the spoken cap warns before the next rebalance flattens.`

- [ ] **Step 5: Targeted tests then full `tests/alphastrategy/`**

Expected: PASS. `paint-*.js` each ≤ 400 lines.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: warn when the live book is through the spoken cap"
```
