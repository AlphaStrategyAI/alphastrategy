# Drift Banner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive the DEVIATION banner from live Book Drift (and a spent last book) so a spent rebalance line cannot hide execution drift.

**Architecture:** Extract `bookDrift` beside `renderBookDrift`. `detectDeviation(portfolio, status)` is true when drift `off > 0` or `last_rebalance_complete === false` with a non-empty `last_combined`. Stop walking audit `resume`/`rebalance` as clearers.

**Tech Stack:** Quiet cockpit JS, `helptext.py`, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-drift-banner-requirements.md`](../requirements/2026-08-20-alphastrategy-drift-banner-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `"Gross cap"` must not appear in assembled JS.
- `renderBanners` keeps a **single** `const reason`.
- Do not retry remaining orders. Do not un-consume `last_rebalance_event`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/paint-portfolio.js`, `src/alphastrategy/web/static/js/boot.js`, `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`, `tests/alphastrategy/test_halt_flatten.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Engine + JS + help**

In `test_restart_before_first_fill_spends_session_window`, after halt assertions add:

```python
    assert restarted.snapshot.last_combined.get("AAPL")
    assert restarted.snapshot.last_combined.get("MSFT")
    assert any(event["event"] == "execution_deviation" for event in events)
```

(Place the `events` read before this if needed; the test already loads `events` after halt.)

In `tests/alphastrategy/test_web_tokens.py`:

```python
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
```

`REQUIRED_PHRASES` add `"deviation banner follows Book Drift"`.

- [ ] **Step 2: Run — FAIL.** Commit tests + docs.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_halt_flatten.py::test_restart_before_first_fill_spends_session_window tests/alphastrategy/test_web_tokens.py::test_js_deviation_banner_follows_book_drift tests/alphastrategy/test_helptext.py::test_help_text_contains_required_phrases -q`

---

### Task 2: Implementation

- [ ] **Step 3: `bookDrift` + `renderBookDrift`**

In `src/alphastrategy/web/static/js/paint-portfolio.js`, immediately before `renderBookDrift`:

```javascript
  function bookDrift(positions, equity) {
    const rows = positions || [];
    const cap = Number(equity);
    let off = 0;
    let maxGap = 0;
    if (!rows.length || !(cap > 0)) {
      return { off: 0, maxGap: 0 };
    }
    const minDelta = Math.max(1, 0.001 * cap);
    for (const pos of rows) {
      if (pos.wanted == null || pos.wanted === undefined) continue;
      const got = Number(pos.weight) || 0;
      const wanted = Number(pos.wanted) || 0;
      const gap = Math.abs(wanted - got);
      if (gap * cap >= minDelta) {
        off += 1;
        if (gap > maxGap) maxGap = gap;
      }
    }
    return { off, maxGap };
  }
```

`renderBookDrift` after the empty/unknown early return uses `const drift = bookDrift(positions, equity)` for `off` / `maxGap` instead of duplicating the loop.

- [ ] **Step 4: `detectDeviation`**

Replace `src/alphastrategy/web/static/js/boot.js` `detectDeviation` with:

```javascript
  function detectDeviation(portfolio, status) {
    const equity = Number(portfolio && portfolio.equity);
    const drift = bookDrift(portfolio && portfolio.positions, equity);
    if (drift.off > 0) return true;
    if (status && status.last_rebalance_complete === false) {
      const combined = portfolio && portfolio.last_combined;
      if (combined && typeof combined === "object" && Object.keys(combined).length) {
        return true;
      }
    }
    return false;
  }
```

In `refresh`: `state.deviationActive = detectDeviation(portfolio, status);` Remove the `portfolio.deviation` / `portfolio.deviations` fork.

- [ ] **Step 5: help + README**

`how_portfolio` after Book Drift: `The deviation banner follows Book Drift and cannot go quiet while Drift is above zero. A spent window keeps it.`

README Operator halt/deviation bullet: the deviation banner follows Book Drift.

- [ ] **Step 6: Full suite PASS.** Commit.

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

---
