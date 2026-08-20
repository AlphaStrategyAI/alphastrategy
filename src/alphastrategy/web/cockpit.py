"""Assemble Quiet cockpit JavaScript from screen-shaped parts."""

from __future__ import annotations

from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent / "static"

JS_PARTS: tuple[str, ...] = (
    "js/core.js",
    "js/paint-rails.js",
    "js/paint-portfolio.js",
    "js/paint-strategies.js",
    "js/paint-run.js",
    "js/paint-activity.js",
    "js/paint-risk.js",
    "js/boot.js",
)

_HEAD = '(function () {\n  "use strict";\n\n'
_TAIL = "})();\n"


def cockpit_js() -> str:
    chunks: list[str] = []
    for rel in JS_PARTS:
        text = (STATIC_DIR / rel).read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        chunks.append(text)
    return _HEAD + "".join(chunks) + _TAIL
