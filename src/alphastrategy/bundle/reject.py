from __future__ import annotations

import zipfile
from typing import Mapping

KINDS = (
    "archive",
    "hash",
    "schema",
    "lineage",
    "evidence",
    "conformance",
    "duplicate",
    "unknown",
)

TITLES: Mapping[str, str] = {
    "archive": "Archive rejected",
    "hash": "Content hash mismatch",
    "schema": "Schema or DSL rejected",
    "lineage": "Lineage rejected",
    "evidence": "Evidence rejected",
    "conformance": "Conformance failed",
    "duplicate": "Already imported",
    "unknown": "Import rejected",
}

NEXT: Mapping[str, str] = {
    "archive": "Use a .asb zip from alphaloop export. No extra files, no .py.",
    "hash": "Re-export the candidate from alphaloop. Do not edit the archive.",
    "schema": "Need a supported schema/DSL pair and us-equity-daily.",
    "lineage": "Only FOUND candidates can be imported.",
    "evidence": "Evidence must declare passes_all: true.",
    "conformance": "Frozen bars must reproduce expected weights. Re-export from alphaloop.",
    "duplicate": "This bundle is already in imported/. Use it on Run.",
    "unknown": "Fix the .asb or re-export from alphaloop.",
}


def infer_kind(message: str) -> str:
    text = (message or "").lower()
    if any(
        needle in text
        for needle in (
            "illegal member",
            "not a zip",
            "bad zipfile",
            "expected multipart",
            "missing multipart",
        )
    ):
        return "archive"
    if "already imported" in text:
        return "duplicate"
    if "hash mismatch" in text or "bundle_id mismatch" in text:
        return "hash"
    if "conformance" in text:
        return "conformance"
    if "research_outcome" in text or "lineage.yaml" in text:
        return "lineage"
    if "passes_all" in text or "evidence/" in text:
        return "evidence"
    if any(
        needle in text
        for needle in (
            "unsupported",
            "missing required",
            "missing field",
            "must be a mapping",
            "secret-like",
            "dsl_version",
            "schema_version",
            "market profile",
            "empty yaml",
            "invalid yaml",
        )
    ):
        return "schema"
    return "unknown"


def payload(exc: BaseException) -> dict[str, str]:
    message = str(exc)
    kind = getattr(exc, "kind", None)
    if kind not in KINDS or kind == "unknown":
        if isinstance(exc, zipfile.BadZipFile):
            kind = "archive"
        else:
            kind = infer_kind(message)
    if kind not in KINDS:
        kind = "unknown"
    return {
        "error": message,
        "kind": str(kind),
        "title": TITLES[kind],
        "next": NEXT[kind],
    }
