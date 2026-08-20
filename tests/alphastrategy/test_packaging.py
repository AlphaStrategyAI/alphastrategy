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
