# Spoken Risk Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Risk and Strategies speak Gross cap / Names / Orders today from one Python map shipped on `GET /api/risk`, while PUT and YAML keep the policy keys.

**Architecture:** `alphastrategy.risk.labels` is the only English map. The control plane copies it onto `GET /api/risk`. The cockpit reads `state.risk.labels` through `policyLabel(key)` and never hardcodes those strings. Tighten math and input names stay the keys.

**Tech Stack:** Python 3, stdlib HTTP API, Quiet cockpit JS, pytest.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-risk-labels-requirements.md`](../requirements/2026-08-20-alphastrategy-risk-labels-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked Quiet cockpit tokens. No `window.confirm`. No live. No WebSockets. No charts.
- Do not rename `AccountPolicy` fields, envelope YAML, audit keys, or `PUT /api/risk` bodies.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Create: `src/alphastrategy/risk/labels.py`
- Modify: `src/alphastrategy/risk/__init__.py`
- Modify: `src/alphastrategy/api/handlers.py`
- Modify: `src/alphastrategy/web/static/app.js`
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_risk.py`, `test_api.py`, `test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Python map + API

**Files:**
- Create: `src/alphastrategy/risk/labels.py`
- Modify: `src/alphastrategy/risk/__init__.py`
- Modify: `src/alphastrategy/api/handlers.py` (`handle_get_risk`)
- Test: `tests/alphastrategy/test_risk.py`, `tests/alphastrategy/test_api.py`, `tests/alphastrategy/test_e2e_mocked.py`

**Interfaces:**
- Consumes: `AccountPolicy` field names
- Produces: `POLICY_LABELS: dict[str, str]`, `label_for(key: str) -> str`, `GET /api/risk` field `labels`

- [ ] **Step 1: Write the failing tests**

Add to `tests/alphastrategy/test_risk.py`:

```python
from dataclasses import fields

from alphastrategy.risk.labels import POLICY_LABELS, label_for
from alphastrategy.risk.policy import AccountPolicy


def test_policy_labels_cover_account_policy_fields() -> None:
    keys = {item.name for item in fields(AccountPolicy)}
    assert set(POLICY_LABELS) == keys
    assert label_for("max_gross") == "Gross cap"
    assert label_for("max_name_weight") == "Name cap"
    assert label_for("max_names") == "Names"
    assert label_for("max_order_notional_frac") == "Order size"
    assert label_for("max_orders_per_rebalance") == "Orders / rebalance"
    assert label_for("max_orders_per_day") == "Orders today"
    assert label_for("min_delta_dollar") == "Min delta $"
    assert label_for("min_delta_frac") == "Min delta % of equity"
    assert label_for("long_only") == "Long only"
    assert label_for("not_a_cap") == "not_a_cap"
```

Add to `tests/alphastrategy/test_api.py` (after `test_status_and_risk_include_utilization`):

```python
def test_get_risk_includes_spoken_labels(api_client: ApiClient) -> None:
    from alphastrategy.risk.labels import POLICY_LABELS

    risk = api_client.get("/api/risk").json()
    assert risk["labels"] == POLICY_LABELS
    assert "max_gross" in risk["account"]
    assert risk["labels"]["max_gross"] == "Gross cap"
```

In `tests/alphastrategy/test_e2e_mocked.py` GET `/` helper (same test that already hits `/api/help` and `/`), also GET `/api/risk` and assert `labels["max_gross"] == "Gross cap"`. If that test does not call `/api/risk`, add the request there:

```python
        conn.request("GET", "/api/risk")
        risk_resp = conn.getresponse()
        risk_body = json.loads(risk_resp.read().decode("utf-8"))
        assert risk_resp.status == 200
        assert risk_body["labels"]["max_gross"] == "Gross cap"
```

- [ ] **Step 2: Run — FAIL**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_risk.py::test_policy_labels_cover_account_policy_fields tests/alphastrategy/test_api.py::test_get_risk_includes_spoken_labels -q`

Expected: FAIL (module missing or `labels` absent).

- [ ] **Step 3: Implement labels + GET**

`src/alphastrategy/risk/labels.py`:

```python
"""Spoken names for AccountPolicy fields. Storage keys stay machine names."""

from __future__ import annotations

POLICY_LABELS: dict[str, str] = {
    "long_only": "Long only",
    "max_gross": "Gross cap",
    "max_name_weight": "Name cap",
    "max_names": "Names",
    "max_order_notional_frac": "Order size",
    "max_orders_per_rebalance": "Orders / rebalance",
    "max_orders_per_day": "Orders today",
    "min_delta_dollar": "Min delta $",
    "min_delta_frac": "Min delta % of equity",
}


def label_for(key: str) -> str:
    return POLICY_LABELS.get(key, key)
```

Export `POLICY_LABELS` and `label_for` from `src/alphastrategy/risk/__init__.py`.

In `handle_get_risk`, add `"labels": dict(POLICY_LABELS)` beside `account` / `sleeves` / `utilization`. Import `POLICY_LABELS` from `alphastrategy.risk.labels`.

- [ ] **Step 4: Tests PASS** for Task 1.

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/risk/labels.py src/alphastrategy/risk/__init__.py src/alphastrategy/api/handlers.py tests/alphastrategy/test_risk.py tests/alphastrategy/test_api.py tests/alphastrategy/test_e2e_mocked.py
git commit -m "feat: ship spoken AccountPolicy labels on GET /api/risk"
```

---

### Task 2: Cockpit painters + help

**Files:**
- Modify: `src/alphastrategy/web/static/app.js` (`policyLabel`, `riskSummary`, `renderRiskCaps`, `buildRiskInputs`)
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_helptext.py`

- [ ] **Step 1: Write the failing tests**

Add to `test_web_tokens.py`:

```python
def test_js_uses_api_policy_labels(js_text: str) -> None:
    assert "function policyLabel" in js_text
    assert "risk.labels" in js_text
    assert "Gross cap" not in js_text
    assert "window.confirm" not in js_text
    nav = None  # nav stays five; HTML fixture still required
```

Keep the HTML five-screen assertion in existing nav tests. Also add to `REQUIRED_PHRASES`: `"Gross cap"`.

- [ ] **Step 2: Run — FAIL** (`policyLabel` missing; help missing Gross cap).

- [ ] **Step 3: Implement**

Add after `riskSummary`'s helpers (near `riskSummary`):

```javascript
  function policyLabel(key) {
    const labels = (state.risk && state.risk.labels) || {};
    const spoken = labels[key];
    return spoken || key;
  }
```

Change `riskSummary`:

```javascript
  function riskSummary(policy) {
    if (!policy) return "—";
    return (
      policyLabel("max_gross") +
      " " +
      fmtPct(policy.max_gross) +
      " · " +
      policyLabel("max_name_weight") +
      " " +
      fmtPct(policy.max_name_weight)
    );
  }
```

In `renderRiskCaps`, the muted span uses `policyLabel(key)` instead of `key`. Same for the `long_only` row (`policyLabel("long_only")`).

In `buildRiskInputs`, `label.textContent = policyLabel(key);` — `input.name` stays `key`.

Help cockpit body: add `Risk names caps in desk words (Gross cap, Names, Orders today). Tighten still posts the policy keys.`

README Quiet cockpit: same sentence.

- [ ] **Step 4: Full suite green**

`PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/web/static/app.js src/alphastrategy/helptext.py README.md tests/alphastrategy/test_web_tokens.py tests/alphastrategy/test_helptext.py
git commit -m "feat: paint Risk and Strategies caps with spoken policy labels"
```

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| Python map covers AccountPolicy | 1 |
| GET /api/risk labels | 1 |
| PUT keys unchanged | 1 (existing put tests) |
| JS policyLabel, no hardcoded Gross cap | 2 |
| Help / README | 2 |
| Five screens / paper / no confirm | existing tests |
