# Operator Help and Architecture Explanation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (this cycle explicitly chose executing-plans). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give operators one canonical how-to (CLI `help`, `GET /api/help`, Quiet-cockpit aside) and a C4-style explanation of the runtime, without adding a sixth nav screen or changing halt/flatten behavior.

**Architecture:** A Python `helptext` module is the single source of operator copy. The CLI prints it; the control plane returns it as JSON; the cockpit renders it in a non-modal aside. Git docs hold Diátaxis explanation (`docs/explanation/architecture.md`) and an index. Argparse stays terse reference.

**Tech Stack:** Existing `argparse` CLI, stdlib HTTP control plane, static Quiet cockpit, pytest. Tests mock the broker.

**Requirements:** [`docs/requirements/2026-08-20-alphastrategy-operator-help-requirements.md`](../requirements/2026-08-20-alphastrategy-operator-help-requirements.md)

## Global Constraints

- Package `alphastrategy`, paper-only walls unchanged.
- Do not grow `src/openstrategy/`.
- Quiet cockpit tokens stay locked. Five `#nav` screens stay exactly Portfolio, Strategies, Run, Activity, Risk.
- Help is an aside, not a modal and not `data-screen="help"`.
- Do not change Supervisor halt/flatten/kill behavior.
- Tests: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`. Never place a real order.

## File map

- Create: `src/alphastrategy/helptext.py` — canonical operator copy
- Create: `docs/index.md` — Diátaxis-lite map
- Create: `docs/explanation/architecture.md` — C4 context + container
- Create: `tests/alphastrategy/test_helptext.py`
- Modify: `src/alphastrategy/cli/main.py` — `help` command, epilog, subcommand help
- Modify: `src/alphastrategy/api/handlers.py` — `GET /api/help`
- Modify: `src/alphastrategy/web/static/index.html` — `#help-toggle`, `#help-panel`
- Modify: `src/alphastrategy/web/static/app.js` — fetch and render help
- Modify: `src/alphastrategy/web/static/styles.css` — aside, not overlay
- Modify: `README.md`, `AGENTS.md`
- Test: `tests/alphastrategy/test_cli.py`, `test_api.py`, `test_web_tokens.py`, `test_e2e_mocked.py`, `test_packaging.py`

---

### Task 1: Canonical helptext module

**Files:**
- Create: `src/alphastrategy/helptext.py`
- Create: `tests/alphastrategy/test_helptext.py`

**Interfaces:**
- Produces: `SECTIONS: list[dict[str, str]]` with keys `id`, `title`, `body`
- Produces: `help_payload() -> dict[str, Any]` with `title` and `sections`
- Produces: `help_text() -> str` titled paragraphs for the terminal

- [ ] **Step 1: Write the failing test**

Create `tests/alphastrategy/test_helptext.py`:

```python
from __future__ import annotations

from alphastrategy.helptext import SECTIONS, help_payload, help_text

REQUIRED_IDS = (
    "identity",
    "execution",
    "halt_flatten",
    "cockpit",
    "cli",
    "walls",
)

REQUIRED_PHRASES = (
    "halt is not flatten",
    "paper only",
    "sole order placer",
    "does not catch up",
    "FLATTEN",
    "Wanted",
    "Got",
)


def test_section_ids_in_order() -> None:
    assert tuple(section["id"] for section in SECTIONS) == REQUIRED_IDS


def test_help_payload_matches_sections() -> None:
    payload = help_payload()
    assert payload["title"] == "alphastrategy operator help"
    assert payload["sections"] == SECTIONS
    for section in payload["sections"]:
        assert section["title"].strip()
        assert section["body"].strip()


def test_help_text_contains_required_phrases() -> None:
    text = help_text()
    lower = text.lower()
    assert "halt is not flatten" in lower
    for phrase in REQUIRED_PHRASES:
        if phrase == "FLATTEN":
            assert "FLATTEN" in text
        elif phrase in ("Wanted", "Got"):
            assert phrase in text
        else:
            assert phrase.lower() in lower


def test_help_copy_is_this_product() -> None:
    blob = help_text().lower() + " ".join(section["body"].lower() for section in SECTIONS)
    assert "streamlit" not in blob
    assert "openstrategy" not in blob
    assert "live trading" not in blob
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'alphastrategy.helptext'`

- [ ] **Step 3: Write minimal implementation**

Create `src/alphastrategy/helptext.py` with this exact content:

```python
"""Canonical operator how-to copy for CLI, API, and Quiet cockpit."""
from __future__ import annotations

from typing import Any

HELP_TITLE = "alphastrategy operator help"

SECTIONS: list[dict[str, str]] = [
    {
        "id": "identity",
        "title": "What this desk is",
        "body": (
            "alphastrategy is a local Alpaca paper execution desk. "
            "alphaloop searches and stress-tests candidates; this product runs "
            "qualified .asb bundles. Import is not permission to trade. Starting "
            "a paper sleeve is a second explicit human action."
        ),
    },
    {
        "id": "execution",
        "title": "How paper execution works",
        "body": (
            "The Supervisor is the sole order placer. Sleeve interpreters return "
            "target weights over stdin/stdout JSON and never see keys or the broker. "
            "Heartbeat every 20 seconds does not place orders. At most two RTH "
            "rebalances fire: open plus 3 minutes, and 12 minutes before close. "
            "combined[asset] = sum(allocation_i * weight_i[asset]). Residual is cash."
        ),
    },
    {
        "id": "halt_flatten",
        "title": "Halt is not flatten",
        "body": (
            "Halt is not flatten. Halt stops new orders and holds positions. "
            "Flatten cancels open orders and trades the paper account (or an "
            "isolated sleeve residual) toward flat. Stop zeros a sleeve on the "
            "next legal rebalance and does not flatten now. Resume after halt "
            "does not catch up; the next legal open or close rebalance does. "
            "Account kill on the Web requires typing FLATTEN."
        ),
    },
    {
        "id": "cockpit",
        "title": "Quiet cockpit",
        "body": (
            "Five screens: Portfolio, Strategies, Run, Activity, Risk. "
            "Wanted is the last combined target weight; Got is the current "
            "position weight. A red FLAT banner means the paper account was "
            "flattened. Help is this aside, not a sixth screen."
        ),
    },
    {
        "id": "cli",
        "title": "CLI verbs",
        "body": (
            "alphastrategy start, import, status, paper start, paper stop, "
            "paper kill, paper resume. paper kill without --bundle flattens "
            "the whole paper account. paper kill --bundle isolates when the "
            "last book is clean; otherwise it flattens the account rather than guess."
        ),
    },
    {
        "id": "walls",
        "title": "Hard walls",
        "body": (
            "Paper only. Control plane binds 127.0.0.1. No live toggle. "
            "No broker credentials in .asb files, logs, or the web UI."
        ),
    },
]


def help_payload() -> dict[str, Any]:
    return {"title": HELP_TITLE, "sections": [dict(section) for section in SECTIONS]}


def help_text() -> str:
    lines = [HELP_TITLE, ""]
    for section in SECTIONS:
        lines.append(section["title"])
        lines.append(section["body"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_helptext.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/helptext.py tests/alphastrategy/test_helptext.py
git commit -m "feat: add canonical operator helptext module"
```

---

### Task 2: CLI help command and argparse reference

**Files:**
- Modify: `src/alphastrategy/cli/main.py`
- Test: `tests/alphastrategy/test_cli.py`

**Interfaces:**
- Consumes: `help_text()` from Task 1
- Produces: `alphastrategy help` prints that text, exit 0, no Alpaca
- Produces: `--help` epilog contains `halt is not flatten` and `alphastrategy help`
- Produces: `paper kill --help` mentions flatten; `paper resume --help` mentions does not catch up; `paper stop --help` mentions next rebalance

- [ ] **Step 1: Write the failing tests**

Append to `tests/alphastrategy/test_cli.py`:

```python
def test_help_command_prints_operator_copy(cli_home: Path, capsys) -> None:
    rc = main(["help"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "halt is not flatten" in out.lower()
    assert "FLATTEN" in out
    assert "sole order placer" in out.lower()


def test_help_command_does_not_construct_alpaca(
    cli_home: Path, patch_alpaca: mock.MagicMock
) -> None:
    rc = main(["help"])
    assert rc == 0
    patch_alpaca.assert_not_called()


def test_top_level_help_epilog_points_to_help_command(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "halt is not flatten" in out.lower()
    assert "alphastrategy help" in out


def test_paper_kill_help_mentions_flatten(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["paper", "kill", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "flatten" in out
    assert "halt" in out


def test_paper_resume_help_mentions_no_catch_up(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["paper", "resume", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "catch up" in out or "catch-up" in out


def test_paper_stop_help_mentions_next_rebalance(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["paper", "stop", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "rebalance" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_cli.py::test_help_command_prints_operator_copy tests/alphastrategy/test_cli.py::test_top_level_help_epilog_points_to_help_command tests/alphastrategy/test_cli.py::test_paper_kill_help_mentions_flatten -q`

Expected: FAIL (`invalid choice: 'help'` and missing flatten in kill help)

- [ ] **Step 3: Write minimal implementation**

In `src/alphastrategy/cli/main.py`:

1. Import `from alphastrategy.helptext import help_text`.
2. Change `create_parser()`:

```python
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alphastrategy",
        description="Local Alpaca paper execution desk for .asb bundles.",
        epilog="Halt is not flatten. Paper only. Run alphastrategy help for the operator runbook.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("help", help="print the operator runbook (halt vs flatten)")

    import_parser = subparsers.add_parser("import", help="import a strategy bundle (.asb)")
    import_parser.add_argument("file", type=Path, help="path to .asb file")

    start_parser = subparsers.add_parser(
        "start",
        help="start localhost Quiet cockpit and Supervisor (paper only)",
    )
    start_parser.add_argument("--host", default=DEFAULT_HOST, help="bind host (v1: localhost only)")
    start_parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="bind port")

    status_parser = subparsers.add_parser("status", help="show supervisor status")
    status_parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="control plane port")

    paper_parser = subparsers.add_parser("paper", help="paper trading controls")
    paper_sub = paper_parser.add_subparsers(dest="paper_command")

    paper_start = paper_sub.add_parser("start", help="start paper sleeve")
    paper_start.add_argument("--bundle", required=True, help="bundle id")
    paper_start.add_argument("--allocation", type=float, required=True, help="allocation 0-1")
    paper_start.add_argument("--port", type=int, default=DEFAULT_PORT, help="control plane port")

    paper_stop = paper_sub.add_parser(
        "stop",
        help="zero that sleeve on the next legal rebalance (does not flatten now)",
    )
    paper_stop.add_argument("--bundle", required=True, help="bundle id")
    paper_stop.add_argument("--port", type=int, default=DEFAULT_PORT, help="control plane port")

    paper_kill = paper_sub.add_parser(
        "kill",
        help="flatten one sleeve, or the whole paper account if --bundle is omitted (not halt)",
    )
    paper_kill.add_argument(
        "--bundle",
        default=None,
        help="bundle id (omit to flatten the whole paper account)",
    )
    paper_kill.add_argument("--port", type=int, default=DEFAULT_PORT, help="control plane port")

    paper_resume = paper_sub.add_parser(
        "resume",
        help="resume from halt; does not catch up and does not flatten",
    )
    paper_resume.add_argument("--port", type=int, default=DEFAULT_PORT, help="control plane port")

    return parser
```

3. In `main()`, after `args = parser.parse_args(argv)` and `home = _home()`, handle help **before** other commands so Alpaca is not constructed:

```python
    if args.command == "help":
        print(help_text(), end="")
        return 0
```

Keep existing empty-argv behavior (`parser.print_help(); return 1`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_cli.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/cli/main.py tests/alphastrategy/test_cli.py
git commit -m "feat: add alphastrategy help and precise CLI verb copy"
```

---

### Task 3: GET /api/help

**Files:**
- Modify: `src/alphastrategy/api/handlers.py`
- Test: `tests/alphastrategy/test_api.py`

**Interfaces:**
- Consumes: `help_payload()` from Task 1
- Produces: `handle_get_help` → 200 JSON; route `("GET", "/api/help")`

- [ ] **Step 1: Write the failing test**

Append to `tests/alphastrategy/test_api.py`:

```python
def test_get_help_returns_operator_sections(api_client: ApiClient) -> None:
    from alphastrategy.helptext import help_payload

    response = api_client.get("/api/help")
    assert response.status == 200
    payload = response.json()
    assert payload["title"] == help_payload()["title"]
    ids = [section["id"] for section in payload["sections"]]
    assert ids == [
        "identity",
        "execution",
        "halt_flatten",
        "cockpit",
        "cli",
        "walls",
    ]
    blob = json_module.dumps(payload)
    assert "secret" not in blob.lower()
    assert "ALPACA" not in blob
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_get_help_returns_operator_sections -q`

Expected: FAIL with HTTP 404 or `not found`

- [ ] **Step 3: Write minimal implementation**

In `src/alphastrategy/api/handlers.py`:

```python
from alphastrategy.helptext import help_payload
```

Add:

```python
def handle_get_help(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    del home, supervisor
    _json_response(handler, 200, help_payload())
```

Register in `dispatch` `routes`:

```python
        ("GET", "/api/help"): handle_get_help,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_api.py::test_get_help_returns_operator_sections tests/alphastrategy/test_api.py::test_get_root_returns_html -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/api/handlers.py tests/alphastrategy/test_api.py
git commit -m "feat: expose GET /api/help operator copy"
```

---

### Task 4: Quiet cockpit Help aside

**Files:**
- Modify: `src/alphastrategy/web/static/index.html`
- Modify: `src/alphastrategy/web/static/styles.css`
- Modify: `src/alphastrategy/web/static/app.js`
- Test: `tests/alphastrategy/test_web_tokens.py`

**Interfaces:**
- Consumes: `GET /api/help` from Task 3
- Produces: `#help-toggle` outside `#nav`; `#help-panel` aside; JS toggle + render; CSS not a modal overlay

- [ ] **Step 1: Write the failing tests**

Append to `tests/alphastrategy/test_web_tokens.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py::test_html_help_is_aside_not_sixth_nav tests/alphastrategy/test_web_tokens.py::test_js_fetches_help_and_toggles_panel -q`

Expected: FAIL missing `#help-toggle`

- [ ] **Step 3: Write minimal implementation**

In `index.html`, wrap `main` and add header button + aside. Replace from `<header>` through `</main>` with:

```html
  <header>
    <div class="brand">alphastrategy · paper</div>
    <nav id="nav" aria-label="Screens">
      <button type="button" data-screen="portfolio" class="active">Portfolio</button>
      <button type="button" data-screen="strategies">Strategies</button>
      <button type="button" data-screen="run">Run</button>
      <button type="button" data-screen="activity">Activity</button>
      <button type="button" data-screen="risk">Risk</button>
    </nav>
    <button type="button" id="help-toggle" aria-expanded="false" aria-controls="help-panel">Help</button>
  </header>

  <div class="shell">
    <main>
      <!-- existing five sections unchanged -->
    </main>
    <aside id="help-panel" class="hidden" aria-label="Operator help">
      <h2>Operator help</h2>
      <div id="help-body"></div>
    </aside>
  </div>
```

Keep every existing screen `section` inside `main` byte-for-byte except for the wrapper.

In `styles.css` append:

```css
.shell {
  display: flex;
  flex: 1;
  min-height: 0;
  align-items: stretch;
}

.shell main {
  flex: 1;
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
}

#help-toggle {
  background: transparent;
  border: 1px solid #2a3142;
  color: #9ba3b4;
  cursor: pointer;
  font: inherit;
  font-size: 0.85rem;
  padding: 0.35rem 0.65rem;
  border-radius: 4px;
}

#help-toggle:hover,
#help-toggle[aria-expanded="true"] {
  color: #e5e9f0;
}

#help-panel {
  width: 22rem;
  max-width: 40%;
  background: #11151d;
  border-left: 1px solid #2a3142;
  padding: 1rem;
  overflow: auto;
  color: #e5e9f0;
}

#help-panel.hidden {
  display: none;
}

#help-panel h2,
#help-panel h3 {
  font-size: 0.85rem;
  font-weight: 600;
  margin: 0 0 0.5rem;
}

#help-panel h3 {
  margin-top: 0.85rem;
  color: #9ba3b4;
}

#help-panel p {
  margin: 0;
  color: #e5e9f0;
  font-size: 0.85rem;
}
```

Change the existing `main { ... }` rule so padding stays; the `.shell main` rule above inherits padding from `main`. Keep:

```css
main {
  flex: 1;
  padding: 1rem;
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
}
```

In `app.js`, add before `refresh();`:

```javascript
  const helpState = { loaded: false };

  function renderHelp(payload) {
    const body = document.getElementById("help-body");
    body.innerHTML = "";
    const title = document.createElement("p");
    title.className = "muted";
    title.textContent = payload.title || "Operator help";
    body.appendChild(title);
    const sections = payload.sections || [];
    for (const section of sections) {
      const h = document.createElement("h3");
      h.textContent = section.title || "";
      const p = document.createElement("p");
      p.textContent = section.body || "";
      body.appendChild(h);
      body.appendChild(p);
    }
  }

  async function loadHelp() {
    const body = document.getElementById("help-body");
    try {
      const payload = await api("GET", "/api/help");
      renderHelp(payload);
      helpState.loaded = true;
    } catch (err) {
      body.textContent = `Help unavailable — ${err.message}`;
    }
  }

  function setHelpOpen(open) {
    const panel = document.getElementById("help-panel");
    const toggle = document.getElementById("help-toggle");
    panel.classList.toggle("hidden", !open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (open && !helpState.loaded) {
      loadHelp();
    }
  }

  document.getElementById("help-toggle").addEventListener("click", () => {
    const open =
      document.getElementById("help-toggle").getAttribute("aria-expanded") === "true";
    setHelpOpen(!open);
  });

  document.addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape") return;
    setHelpOpen(false);
  });
```

Do not change `showScreen` to know about help.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_web_tokens.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/alphastrategy/web/static/index.html src/alphastrategy/web/static/styles.css src/alphastrategy/web/static/app.js tests/alphastrategy/test_web_tokens.py
git commit -m "feat: add Quiet cockpit operator help aside"
```

---

### Task 5: Explanation docs, README architecture, AGENTS.md

**Files:**
- Create: `docs/index.md`
- Create: `docs/explanation/architecture.md`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Test: `tests/alphastrategy/test_packaging.py`

**Interfaces:**
- Produces: docs map + C4 explanation; README runtime diagram; AGENTS.md alphastrategy identity

- [ ] **Step 1: Write the failing tests**

Append to `tests/alphastrategy/test_packaging.py`:

```python
DOCS_INDEX = ROOT / "docs" / "index.md"
ARCHITECTURE = ROOT / "docs" / "explanation" / "architecture.md"
AGENTS = ROOT / "AGENTS.md"


def test_docs_index_maps_diataxis() -> None:
    text = DOCS_INDEX.read_text(encoding="utf-8")
    assert "docs/requirements/2026-08-19-alphastrategy-v1-requirements.md" in text
    assert "docs/explanation/architecture.md" in text
    assert "docs/plans/" in text


def test_architecture_explanation_has_c4_runtime() -> None:
    text = ARCHITECTURE.read_text(encoding="utf-8")
    lower = text.lower()
    assert "supervisor" in lower
    assert "alpaca" in lower
    assert "alphaloop" in lower
    assert "paper" in lower
    assert "sole" in lower or "only order" in lower


def test_readme_architecture_is_runtime_not_only_tree() -> None:
    text = README.read_text(encoding="utf-8")
    assert "docs/index.md" in text
    assert "docs/explanation/architecture.md" in text
    assert "Supervisor" in text
    assert "control plane" in text.lower()


def test_agents_md_describes_alphastrategy() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    lower = text.lower()
    assert "alphastrategy" in lower
    assert "tests/alphastrategy" in text
    assert "streamlit run" not in lower
    assert "openstrategy report" not in lower
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_packaging.py::test_docs_index_maps_diataxis tests/alphastrategy/test_packaging.py::test_agents_md_describes_alphastrategy -q`

Expected: FAIL missing `docs/index.md`

- [ ] **Step 3: Write the documents**

Create `docs/index.md`:

```markdown
# alphastrategy documentation

How to find the right document. Names follow Diátaxis (how-to, reference, explanation) without renaming existing requirement files.

## Start here

- Product contract (reference): [`docs/requirements/2026-08-19-alphastrategy-v1-requirements.md`](requirements/2026-08-19-alphastrategy-v1-requirements.md)
- Operator how-to: [README](../README.md) and in-desk **Help** (`alphastrategy help`, `GET /api/help`)
- Runtime explanation: [`docs/explanation/architecture.md`](explanation/architecture.md)

## Reference (what must be true)

- [`docs/requirements/`](requirements/) — v1 plus later improvement contracts
- CLI verbs: `alphastrategy --help` (reference) and `alphastrategy help` (runbook)

## Explanation (why it is this way)

- [`docs/explanation/architecture.md`](explanation/architecture.md)

## Plans (how it was built)

- [`docs/plans/`](plans/)

## Lessons

- [`docs/lessons/`](lessons/)
```

Create `docs/explanation/architecture.md` with a C4 context mermaid and a C4 container mermaid, plus prose that alphaloop is export-only, Supervisor is the sole order placer, heartbeat does not order, one paper account, loopback control plane. Include the v1 ASCII:

```text
Web / CLI
    |
    v
Local control plane (localhost)
    |
    v
Supervisor  <-- sole holder of Alpaca keys and sole order placer
    |
    +-- sleeve interpreters (one sandbox process per running bundle)
```

Rewrite `AGENTS.md` to this product (keep environment notes that still apply: `.venv`, python3.12-venv) but replace OpenStrategy/Streamlit/report instructions with alphastrategy test and start commands.

Update README Architecture to the runtime ASCII above, keep a short module tree, and add links to `docs/index.md` and `docs/explanation/architecture.md`. Add a line under Operator that in-desk Help and `alphastrategy help` carry the same runbook.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_packaging.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/index.md docs/explanation/architecture.md README.md AGENTS.md tests/alphastrategy/test_packaging.py
git commit -m "docs: add architecture explanation, docs index, and alphastrategy AGENTS.md"
```

---

### Task 6: Integration and e2e for help

**Files:**
- Modify: `tests/alphastrategy/test_e2e_mocked.py`
- Modify: `tests/alphastrategy/test_api.py` (root HTML includes help control)

**Interfaces:**
- Consumes: Tasks 3–4
- Produces: mocked-broker e2e that `/` and `/api/help` work on a live control plane

- [ ] **Step 1: Write the failing tests**

In `test_api.py` extend `test_get_root_returns_html` or add:

```python
def test_get_root_includes_help_control(api_client: ApiClient) -> None:
    response = api_client.get("/")
    assert response.status == 200
    html = response.body.decode("utf-8")
    assert 'id="help-toggle"' in html
    assert 'id="help-panel"' in html
    assert 'data-screen="help"' not in html
```

Append to `tests/alphastrategy/test_e2e_mocked.py`:

```python
def test_control_plane_serves_help(tmp_path: Path) -> None:
    home = AlphaStrategyHome(root=tmp_path)
    home.root.mkdir(parents=True, exist_ok=True)
    broker = FakeBroker()
    supervisor = _make_supervisor(home, broker)
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/api/help")
        help_resp = conn.getresponse()
        help_body = json.loads(help_resp.read().decode("utf-8"))
        assert help_resp.status == 200
        assert help_body["sections"][2]["id"] == "halt_flatten"
        conn.request("GET", "/")
        html_resp = conn.getresponse()
        html = html_resp.read().decode("utf-8")
        assert html_resp.status == 200
        assert 'id="help-toggle"' in html
    finally:
        server.shutdown()
        thread.join(timeout=2)
```

If `test_get_root_returns_html` already exists, keep it; the new test is additive.

- [ ] **Step 2: Run tests**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/test_e2e_mocked.py::test_control_plane_serves_help tests/alphastrategy/test_api.py::test_get_root_includes_help_control -q`

Expected: PASS if Task 4 is done; FAIL only if Help markup or route is missing.

- [ ] **Step 3: Fix any failures**

If FakeBroker construction in e2e differs, copy the constructor used by `test_v1_done_path` in the same file.

- [ ] **Step 4: Run the full alphastrategy suite**

Run: `PYTHONPATH=src python3 -m pytest tests/alphastrategy/ -q`

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/alphastrategy/test_e2e_mocked.py tests/alphastrategy/test_api.py
git commit -m "test: e2e control plane serves operator help"
```

---

## Spec coverage (self-review)

| Requirement | Task |
| --- | --- |
| Canonical `helptext` + required phrases | 1 |
| `alphastrategy help`, argparse epilog, kill/resume/stop copy | 2 |
| `GET /api/help` | 3 |
| Help aside, not sixth nav, Escape, fetch | 4 |
| `docs/index.md`, architecture explanation, README, AGENTS.md | 5 |
| E2E + root HTML | 6 |
| No live, no behavior change to kill | Global constraints |

No TBD placeholders. No sixth screen. No Supervisor behavior change.
