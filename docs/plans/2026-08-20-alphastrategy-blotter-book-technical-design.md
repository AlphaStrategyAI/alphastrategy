# Activity Blotter Book Drill-In Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Activity row expand JSON with a Wanted / Got book table (and labeled fields for other events).

**Architecture:** Client-only in `js/paint-activity.js`. Audit schema and `#activity-list` stay. `eventDetail(ev)` builds a `.activity-detail` div; `bookTable(wanted, got)` builds `.activity-book`. No new API.

**Tech Stack:** Cockpit JS parts, CSS, `helptext.py`, pytest string tests, e2e GET `/app.js`.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-blotter-book-requirements.md`](../requirements/2026-08-20-alphastrategy-blotter-book-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Locked tokens. No `window.confirm`. No live.
- `GET /api/activity` unchanged. Expand still one row at a time.
- Edit `js/paint-activity.js`, not a file named `app.js`. File stays ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/js/paint-activity.js`, `styles.css`
- Modify: `src/alphastrategy/helptext.py`, `README.md`
- Test: `tests/alphastrategy/test_web_tokens.py`, `test_helptext.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`tests/alphastrategy/test_web_tokens.py` (append):

```python
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
```

`REQUIRED_PHRASES` add `"not a JSON dump"`.

`test_control_plane_serves_help`: after GET `/`, also:

```python
        conn.request("GET", "/app.js")
        js_resp = conn.getresponse()
        js_body = js_resp.read().decode("utf-8")
        assert js_resp.status == 200
        assert "function bookTable" in js_body
        assert "JSON.stringify(payload" not in js_body
```

- [ ] **Step 2: Run — FAIL.** Commit tests.

---

### Task 2: Painter, CSS, help

- [ ] **Step 4: Painter**

In `src/alphastrategy/web/static/js/paint-activity.js`, after `eventSummary` and before `renderActivity`, add:

```javascript
  function formatField(value) {
    if (value == null || value === "") return "—";
    if (typeof value !== "object") return String(value);
    const keys = Object.keys(value);
    if (!keys.length) return "—";
    return keys
      .sort()
      .map((k) => `${k} ${value[k]}`)
      .join(" · ");
  }

  function detailList(rows) {
    const dl = document.createElement("dl");
    dl.className = "activity-fields";
    for (const [label, value] of rows) {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.className = "nums";
      dd.textContent = formatField(value);
      dl.appendChild(dt);
      dl.appendChild(dd);
    }
    return dl;
  }

  function bookTable(wanted, got) {
    const table = document.createElement("table");
    table.className = "activity-book";
    table.innerHTML = "<thead><tr><th>Symbol</th><th>Wanted</th><th>Got</th></tr></thead>";
    const tbody = document.createElement("tbody");
    const keys = [...new Set([...Object.keys(wanted || {}), ...Object.keys(got || {})])].sort();
    if (!keys.length) {
      tbody.innerHTML = "<tr><td colspan='3' class='muted'>—</td></tr>";
    } else {
      for (const key of keys) {
        const tr = document.createElement("tr");
        tr.innerHTML =
          `<td>${key}</td>` +
          `<td class="nums">${fmtPct(wanted && wanted[key])}</td>` +
          `<td class="nums">${fmtPct(got && got[key])}</td>`;
        tbody.appendChild(tr);
      }
    }
    table.appendChild(tbody);
    return table;
  }

  function eventDetail(ev) {
    const wrap = document.createElement("div");
    wrap.className = "activity-detail";
    const kind = ev.event;
    if (kind === "rebalance") {
      wrap.appendChild(bookTable(ev.wanted, ev.got));
      wrap.appendChild(
        detailList([
          ["Session", ev.session_event],
          ["Orders", ev.orders],
        ])
      );
      return wrap;
    }
    if (kind === "execution_deviation") {
      const asset = ev.asset || "—";
      wrap.appendChild(bookTable({ [asset]: ev.wanted }, { [asset]: ev.got }));
      return wrap;
    }
    if (kind === "order") {
      wrap.appendChild(
        detailList([
          ["Symbol", ev.symbol],
          ["Side", ev.side],
          ["Qty", ev.qty],
        ])
      );
      return wrap;
    }
    if (kind === "halt") {
      wrap.appendChild(detailList([["Reason", ev.reason]]));
      return wrap;
    }
    if (kind === "kill") {
      const outcome = ev.isolated === true ? "isolated residual" : "flattened account";
      wrap.appendChild(
        detailList([
          ["Outcome", outcome],
          ["Bundle", ev.bundle_id],
          ["Scope", ev.scope],
        ])
      );
      return wrap;
    }
    if (kind === "flatten") {
      wrap.appendChild(detailList([["Scope", ev.scope || "account"]]));
      return wrap;
    }
    if (kind === "paper_start" || kind === "paper_stop" || kind === "import") {
      wrap.appendChild(detailList([["Bundle", ev.bundle_id || ev.scope]]));
      return wrap;
    }
    const rows = Object.keys(ev)
      .filter((key) => key !== "ts" && key !== "timestamp" && key !== "event")
      .sort()
      .map((key) => [key, ev[key]]);
    wrap.appendChild(detailList(rows.length ? rows : [["Detail", "—"]]));
    return wrap;
  }
```

In `renderActivity`, replace the `<pre>` block with:

```javascript
      li.appendChild(summary);
      li.appendChild(eventDetail(ev));
```

Keep expand click / keyboard handlers.

- [ ] **Step 5: CSS**

Replace `.activity-detail` and add after it in `styles.css`:

```css
.activity-detail {
  display: none;
  color: #9ba3b4;
  margin: 0.35rem 0 0;
  font: inherit;
}

.activity-list li.expanded .activity-detail {
  display: block;
}

.activity-book {
  margin: 0.15rem 0 0.5rem;
}

.activity-fields {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.2rem 0.75rem;
  margin: 0;
  font-size: 0.85rem;
}

.activity-fields dt {
  color: #9ba3b4;
}

.activity-fields dd {
  margin: 0;
  color: #e5e9f0;
}
```

Keep the existing `li.expanded` rule (do not duplicate if the replace already includes it).

- [ ] **Step 6: Help + README**

`how_activity` last sentence:

```python
            "Expand a blotter row for a Wanted / Got table, not a JSON dump."
```

Cockpit, after the Activity bands sentence:

```text
Expanding a blotter row shows Wanted versus Got, not a JSON dump.
```

README Quiet cockpit, after the Activity bands sentence:

```text
Expanding a blotter row shows **Wanted / Got**, not a JSON dump.
```

- [ ] **Step 8: Full suite PASS. Commit.**

---

## Spec coverage

Drill-in table, labeled fields, no JSON payload dump, CSS, help, e2e `/app.js` — tasked. No placeholders.
