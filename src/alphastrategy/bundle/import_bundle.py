from __future__ import annotations

import json
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
from alphastrategy.errors import ImportRejected
from alphastrategy.home import AlphaStrategyHome


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
            f"content hash mismatch: expected {manifest.content_hash}, got {computed_hash}"
        )
    expected_id = bundle_id_from_hash(computed_hash)
    if manifest.bundle_id != expected_id:
        raise ImportRejected(
            f"bundle_id mismatch: expected {expected_id}, got {manifest.bundle_id}"
        )

    load_parameters(members["parameters.yaml"])
    load_risk_envelope(members["risk-envelope.yaml"])
    load_strategy_dsl(members["strategy.dsl.yaml"])
    load_conformance_expected(members["conformance/expected_weights.yaml"])

    bundle_id = manifest.bundle_id
    bundle_dir = home.bundle_dir(bundle_id)
    if bundle_dir.exists():
        raise ImportRejected(f"bundle already imported: {bundle_id}")

    bundle_dir.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in sorted(members.items()):
            dest = bundle_dir / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

        meta = {
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "source_path": str(path.resolve()),
        }
        (bundle_dir / "import-meta.json").write_text(
            json.dumps(meta, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        import shutil

        shutil.rmtree(bundle_dir, ignore_errors=True)
        raise

    return bundle_id
