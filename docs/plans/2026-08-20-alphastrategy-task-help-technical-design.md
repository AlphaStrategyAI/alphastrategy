# Task-Shaped Operator How-Tos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this cycle chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add job how-tos (import, start paper, flatten, tighten, wanted vs got) so F1 and `alphastrategy help` answer work, not only screen maps.

**Architecture:** `TASK_HOWTOS` in `helptext.py`. `help_payload()` adds `tasks`. CLI prints tasks first. Cockpit `#help-tasks` filters by `item.screens` and the active nav screen. Do not copy job strings into JS. Do not revive `static/app.js`.

**Tech Stack:** Python `helptext`, cockpit `js/boot.js`, pytest, e2e GET `/api/help` and `/`.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-task-help-requirements.md`](../requirements/2026-08-20-alphastrategy-task-help-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. Help is an aside. Locked tokens. No `window.confirm`. No live.
- Keep `SCREEN_HOWTOS` and `SECTIONS` ids. Edit `js/boot.js`, not a file named `app.js`. `boot.js` stays ≤ 400 lines.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/helptext.py`, `web/static/index.html`, `js/boot.js`, `README.md`
- Test: `tests/alphastrategy/test_helptext.py`, `test_api.py`, `test_web_tokens.py`, `test_e2e_mocked.py`

---

### Task 1: Failing tests

- [ ] **Step 1: Write the failing tests**

`tests/alphastrategy/test_helptext.py` — add `"How to import a qualified .asb"` to `REQUIRED_PHRASES`. Append:

```python
def test_task_howtos_match_jobs() -> None:
    from alphastrategy.helptext import TASK_HOWTOS

    assert tuple(item["id"] for item in TASK_HOWTOS) == (
        "task_import",
        "task_start",
        "task_flatten",
        "task_tighten",
        "task_wanted",
    )
    payload = help_payload()
    assert payload["tasks"] == TASK_HOWTOS
    assert payload["howtos"][0]["id"] == "how_portfolio"
    text = help_text()
    assert text.index("How to import a qualified .asb") < text.index("On Portfolio")
    for item in TASK_HOWTOS:
        assert item["title"].startswith("How to")
        assert item["body"].strip()
        assert item["screens"]
        for screen in item["screens"]:
            assert screen in ("portfolio", "strategies", "run", "activity", "risk")
```

Also include `TASK_HOWTOS` in `test_help_copy_is_this_product` blob.

`tests/alphastrategy/test_api.py` `test_get_help_returns_operator_sections`:

```python
    assert [item["id"] for item in payload["tasks"]] == [
        "task_import",
        "task_start",
        "task_flatten",
        "task_tighten",
        "task_wanted",
    ]
```

`tests/alphastrategy/test_web_tokens.py`:

```python
def test_html_help_tasks(html_text: str) -> None:
    assert 'id="help-tasks"' in html_text
    assert 'id="help-howto"' in html_text
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
```

e2e `test_control_plane_serves_help`: `assert help_body["tasks"][0]["id"] == "task_import"` and `assert 'id="help-tasks"' in html`.

- [ ] **Step 2: Run — FAIL.** Commit tests.

---

### Task 2: helptext, HTML, painter, README

- [ ] **Step 4: `TASK_HOWTOS`**

In `src/alphastrategy/helptext.py` after `SCREEN_HOWTOS`:

```python
TASK_HOWTOS: list[dict[str, Any]] = [
    {
        "id": "task_import",
        "screens": ["strategies"],
        "title": "How to import a qualified .asb",
        "body": (
            "1. Open Strategies (Alt+2). "
            "2. Under Import .asb choose the file and Upload. "
            "3. If rejected, the gate (hash, schema, conformance) and a next action are named. "
            "Import is not permission to trade."
        ),
    },
    {
        "id": "task_start",
        "screens": ["strategies", "run"],
        "title": "How to start a paper sleeve",
        "body": (
            "1. Import first if Inventory is empty. "
            "2. Open Run (Alt+3). "
            "3. Under Start paper pick the bundle, set allocation, check Confirm paper start, then Start paper. "
            "This is the second explicit action."
        ),
    },
    {
        "id": "task_flatten",
        "screens": ["run"],
        "title": "How to flatten the paper account",
        "body": (
            "1. Open Run (Alt+3). "
            "2. Under Flatten account — not After halt — check the box, type FLATTEN, then Kill account. "
            "Halt is not flatten. Resume does not catch up."
        ),
    },
    {
        "id": "task_tighten",
        "screens": ["risk"],
        "title": "How to tighten a cap",
        "body": (
            "1. Open Risk (Alt+5). "
            "2. Caps and Headroom stay sticky. "
            "3. Under Tighten change only Gross / Names / Orders / Deltas fields you mean to tighten, then Tighten. "
            "Looser values are refused; PUT keys stay machine names."
        ),
    },
    {
        "id": "task_wanted",
        "screens": ["portfolio", "activity"],
        "title": "How to read wanted versus got",
        "body": (
            "1. On Portfolio, Positions Wanted versus Got is last combined target versus current weight. "
            "2. On Activity, expand a rebalance blotter row for the Wanted / Got table, not a JSON dump."
        ),
    },
]
```

`help_payload`:

```python
        "howtos": [dict(item) for item in SCREEN_HOWTOS],
        "tasks": [dict(item) for item in TASK_HOWTOS],
```

`help_text`: loop `TASK_HOWTOS` **before** `SCREEN_HOWTOS`.

Cockpit section, after the F1 sentence:

```text
F1 shows the screen how-to and the jobs for that screen.
```

- [ ] **Step 5: HTML**

In `index.html` aside, after `#help-howto`:

```html
      <div id="help-tasks"></div>
```

- [ ] **Step 6: `renderHelp` in `js/boot.js`**

After painting `#help-howto`, before `#help-body`:

```javascript
    const taskRoot = document.getElementById("help-tasks");
    if (taskRoot) {
      taskRoot.innerHTML = "";
      const tasks = helpState.payload.tasks || [];
      for (const item of tasks) {
        const screens = item.screens || [];
        if (screens.indexOf(screen) < 0) continue;
        const th = document.createElement("h3");
        th.textContent = item.title || "";
        const tp = document.createElement("p");
        tp.textContent = item.body || "";
        taskRoot.appendChild(th);
        taskRoot.appendChild(tp);
      }
    }
```

Keep fetch errors on `#help-howto`. `boot.js` ≤ 400 lines.

- [ ] **Step 7: README**

Quiet cockpit, after the Help sentences:

```text
`alphastrategy help` prints **How to** jobs first. F1 shows the jobs for the
current screen (import, start paper, flatten, tighten, wanted versus got).
```

- [ ] **Step 8: Full suite PASS. Commit.**

---

## Spec coverage

Five jobs, payload `tasks`, CLI order, `#help-tasks` filter, tests — tasked. No placeholders.
