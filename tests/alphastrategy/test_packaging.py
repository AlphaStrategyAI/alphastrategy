from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
README = ROOT / "README.md"


def test_pyproject_alphastrategy_identity() -> None:
    text = PYPROJECT.read_text()
    assert 'name = "alphastrategy"' in text
    assert 'version = "0.1.0"' in text
    assert "[project.scripts]" in text
    assert 'alphastrategy = "alphastrategy.cli.main:main"' in text
    assert "openstrategy =" not in text
    assert 'packages = ["src/alphastrategy"]' in text
    assert "https://github.com/AlphaStrategyAI/alphastrategy" in text


def test_readme_paper_desk_positioning() -> None:
    text = README.read_text()
    lower = text.lower()
    assert "paper" in lower
    assert "alphaloop" in lower
    assert "halt" in lower
    assert "flatten" in lower
    assert "find alpha" not in lower
    assert "guaranteed" not in lower
    for line in text.splitlines():
        stripped = line.lower().strip()
        if "promise" in stripped and "alpha" in stripped:
            assert any(
                neg in stripped for neg in ("not promise", "does not promise", "don't promise")
            ), f"README must not promise alpha: {line!r}"


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
