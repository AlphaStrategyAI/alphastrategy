from __future__ import annotations

import csv
import io
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from alphastrategy.bundle.archive import read_asb
from alphastrategy.bundle.hash import bundle_id_from_hash, content_hash
from alphastrategy.bundle.schema import (
    load_bundle_manifest,
    load_conformance_expected,
    load_evidence_summary,
    load_lineage,
    load_market_profile,
    load_parameters,
    load_risk_envelope,
    load_strategy_dsl,
    require_members,
)
from alphastrategy.dsl.sandbox import run_sandbox, weights_match
from alphastrategy.errors import HaltRequested, ImportRejected
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.persist import fsync_dir, replace_bytes, replace_text


def _bars_from_csv(data: bytes) -> dict:
    reader = csv.DictReader(io.StringIO(data.decode()))
    if not reader.fieldnames or "date" not in reader.fieldnames:
        raise ImportRejected("conformance/bars.csv missing date column", kind="conformance")
    symbols = [c for c in reader.fieldnames if c != "date"]
    rows = list(reader)
    bars: dict = {"date": [row["date"] for row in rows]}
    for sym in symbols:
        bars[sym] = [float(row[sym]) for row in rows]
    return bars


def _run_conformance(staging: Path, members: dict[str, bytes]) -> None:
    expected = load_conformance_expected(members["conformance/expected_weights.yaml"])
    bars = _bars_from_csv(members["conformance/bars.csv"])
    try:
        got = run_sandbox(staging, bars, expected.effective_at)
    except HaltRequested as exc:
        raise ImportRejected(f"conformance sandbox failed: {exc}", kind="conformance") from exc
    if not weights_match(got, expected.weights):
        raise ImportRejected("conformance weights mismatch", kind="conformance")


def import_asb(path: Path, home: AlphaStrategyHome) -> str:
    members = read_asb(path)
    require_members(members)

    manifest = load_bundle_manifest(members["bundle.yaml"])

    load_market_profile(members["market-profile.yaml"])
    load_lineage(members["lineage.yaml"])
    load_evidence_summary(members["evidence/summary.yaml"])

    computed_hash = content_hash(members)
    if manifest.content_hash != computed_hash:
        raise ImportRejected(
            f"content hash mismatch: expected {manifest.content_hash}, got {computed_hash}",
            kind="hash",
        )
    expected_id = bundle_id_from_hash(computed_hash)
    if manifest.bundle_id != expected_id:
        raise ImportRejected(
            f"bundle_id mismatch: expected {expected_id}, got {manifest.bundle_id}",
            kind="hash",
        )

    load_parameters(members["parameters.yaml"])
    load_risk_envelope(members["risk-envelope.yaml"])
    strategy_dsl = load_strategy_dsl(members["strategy.dsl.yaml"])
    if strategy_dsl.dsl_version != manifest.dsl_version:
        raise ImportRejected(
            "strategy.dsl.yaml dsl_version does not match bundle.yaml: "
            f"{strategy_dsl.dsl_version} != {manifest.dsl_version}",
            kind="schema",
        )
    load_conformance_expected(members["conformance/expected_weights.yaml"])

    bundle_id = manifest.bundle_id
    bundle_dir = home.bundle_dir(bundle_id)
    if bundle_dir.exists():
        raise ImportRejected(f"bundle already imported: {bundle_id}", kind="duplicate")

    imported = home.imported_dir()
    imported.mkdir(parents=True, exist_ok=True)
    staging_parent = Path(tempfile.mkdtemp(prefix=".staging.", dir=imported))
    staging = staging_parent / bundle_id
    staging.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in sorted(members.items()):
            dest = staging / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            replace_bytes(dest, data, prefix=".member.")
        fsync_dir(staging)

        _run_conformance(staging, members)

        meta = {
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "source_path": str(path.resolve()),
        }
        replace_text(
            staging / "import-meta.json",
            json.dumps(meta, indent=2) + "\n",
            prefix=".meta.",
        )
        os.replace(staging, bundle_dir)
        fsync_dir(imported)
    except Exception:
        shutil.rmtree(staging_parent, ignore_errors=True)
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir, ignore_errors=True)
        raise
    finally:
        if staging_parent.exists():
            shutil.rmtree(staging_parent, ignore_errors=True)

    return bundle_id
