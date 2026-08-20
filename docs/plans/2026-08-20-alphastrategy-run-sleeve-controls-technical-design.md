# Run Sleeve Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (this cycle explicitly chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an operator set each sleeve’s allocation on the Run card with an explicit confirm, and require a checkbox before sleeve kill, without poll-wiping in-progress inputs.

**Architecture:** Reuse `POST /api/paper/start` and `POST /api/paper/kill`. All new behavior is Quiet-cockpit JS plus static tests. No Supervisor change.

**Tech Stack:** Static Quiet cockpit, pytest string tests, existing mocked API.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-run-sleeve-controls-requirements.md`](../requirements/2026-08-20-alphastrategy-run-sleeve-controls-requirements.md)

## Global Constraints

- Paper only. Five `#nav` screens. No `window.confirm`. Account kill still requires `FLATTEN`.
- Do not grow `src/openstrategy/`.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`.

## File map

- Modify: `src/alphastrategy/web/static/app.js` — `renderRunSleeves`, `runFormIsDirty`, refresh skip
- Test: `tests/alphastrategy/test_web_tokens.py`, `tests/alphastrategy/test_e2e_mocked.py`

---

### Task 1: Failing web tests for Run cards

**Files:**
- Modify: `tests/alphastrategy/test_web_tokens.py`

- [ ] **Step 1: Write the failing tests**

Append:

```python
def test_js_run_sleeve_allocation_and_kill_confirm(js_text: str) -> None:
    assert "sleeve-alloc-form" in js_text
    assert "Confirm paper allocation" in js_text
    assert "Set allocation" in js_text
    assert "data-kill-confirm" in js_text
    assert "Confirm sleeve kill" in js_text
    assert "runFormIsDirty" in js_text
    assert "Confirm paper allocation required" in js_text
    assert "Confirm sleeve kill" in js_text
    assert "window.confirm" not in js_text
    assert "/api/paper/start" in js_text
```

- [ ] **Step 2: Run to verify FAIL**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_run_sleeve_allocation_and_kill_confirm -q`

Expected: FAIL missing `sleeve-alloc-form`

- [ ] **Step 3: Implement `runFormIsDirty`, card form, kill checkbox**

In `src/alphastrategy/web/static/app.js` replace `renderRunSleeves` with:

```javascript
  function runFormIsDirty() {
    const container = document.getElementById("run-sleeves");
    if (!container) return false;
    if (container.contains(document.activeElement)) return true;
    const inputs = container.querySelectorAll("input");
    for (const input of inputs) {
      if (input.type === "checkbox") {
        if (input.checked) return true;
        continue;
      }
      if (input.name === "allocation" && input.value !== input.dataset.current) {
        return true;
      }
    }
    return false;
  }

  function renderRunSleeves() {
    const bundles = state.bundles || { imported: [], paper: {} };
    const container = document.getElementById("run-sleeves");
    container.innerHTML = "";

    const ids = [...new Set([...bundles.imported, ...Object.keys(bundles.paper)])].sort();
    for (const id of ids) {
      const card = document.createElement("div");
      card.className = "sleeve-card panel";
      const alloc = bundles.paper[id] || 0;
      card.innerHTML = `
        <h3>${id}</h3>
        <form class="inline sleeve-alloc-form" data-bundle="${id}">
          <label>
            Allocation
            <input type="number" min="0" max="1" step="0.01" name="allocation" value="${alloc}" data-current="${alloc}" required>
          </label>
          <label class="confirm-row">
            <input type="checkbox" name="confirm">
            Confirm paper allocation
          </label>
          <button type="submit" class="action primary">Set allocation</button>
        </form>
        <div class="inline">
          <button type="button" class="action warn" data-stop="${id}">Stop</button>
          <label class="confirm-row">
            <input type="checkbox" data-kill-confirm="${id}">
            Confirm sleeve kill
          </label>
          <button type="button" class="action danger" data-kill="${id}">Kill sleeve</button>
        </div>
      `;
      container.appendChild(card);
    }

    container.querySelectorAll(".sleeve-alloc-form").forEach((form) => {
      form.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const errEl = document.getElementById("run-error");
        const bundleId = form.dataset.bundle;
        const allocation = Number(form.querySelector('[name="allocation"]').value);
        const confirmed = form.querySelector('[name="confirm"]').checked;
        if (!confirmed) {
          setError(errEl, "Confirm paper allocation required");
          return;
        }
        try {
          await api("POST", "/api/paper/start", { bundle_id: bundleId, allocation });
          setError(errEl, "");
          await refresh();
        } catch (err) {
          setError(errEl, err.message);
        }
      });
    });

    container.querySelectorAll("[data-stop]").forEach((btn) => {
      btn.addEventListener("click", () => stopSleeve(btn.dataset.stop));
    });
    container.querySelectorAll("[data-kill]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const bundleId = btn.dataset.kill;
        const box = container.querySelector(`[data-kill-confirm="${bundleId}"]`);
        if (!box || !box.checked) {
          setError(document.getElementById("run-error"), "Confirm sleeve kill");
          return;
        }
        killSleeve(bundleId);
      });
    });
  }
```

In `refresh()`, after `renderStrategies();` call `renderRunSleeves` only when not dirty:

```javascript
      renderStrategies();
      if (!runFormIsDirty()) {
        renderRunSleeves();
      }
      renderActivity();
```

Place `runFormIsDirty` **above** `renderRunSleeves` (replace the current function in situ so `refresh` can see it — both are in the same IIFE).

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/web/static/app.js tests/alphastrategy/test_web_tokens.py
git commit -m "feat: per-sleeve allocation and sleeve-kill confirm on Run"
```

---

### Task 2: E2E HTML still has five screens; kill still not FLATTEN on cards

**Files:**
- Modify: `tests/alphastrategy/test_e2e_mocked.py` or `test_web_tokens.py`

- [ ] **Step 1: Write the test**

Append to `test_web_tokens.py`:

```python
def test_js_sleeve_kill_does_not_require_flatten_phrase(js_text: str) -> None:
    kill_fn = js_text.split("async function killSleeve")[1].split("async function onImportSubmit")[0]
    assert "FLATTEN" not in kill_fn
    assert "data-kill-confirm" in js_text
```

- [ ] **Step 2: Run**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_js_sleeve_kill_does_not_require_flatten_phrase tests/alphastrategy/test_api.py::test_start_replaces_existing_sleeve_allocation tests/alphastrategy/test_web_tokens.py::test_html_contains_five_nav_labels -q`

Expected: PASS

- [ ] **Step 3: Full suite**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all PASS

- [ ] **Step 4: Commit** if the new test file change was not in Task 1

```bash
git add tests/alphastrategy/test_web_tokens.py
git commit -m "test: sleeve kill confirm is quieter than account FLATTEN"
```

---

## Spec coverage

| Requirement | Task |
| --- | --- |
| Per-card allocation + confirm + `/api/paper/start` | 1 |
| Dirty skip | 1 |
| Sleeve kill checkbox, no `window.confirm`, no `FLATTEN` | 1–2 |
| Existing start replace + five screens | 2 |
