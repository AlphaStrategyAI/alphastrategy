from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from alphastrategy.errors import ImportRejected

SUPPORTED = {("alphastrategy.bundle/v0", "alphaloop.dsl/v0")}

_SECRET_FRAGMENTS = ("key", "secret", "token", "password", "credential")

_REQUIRED_MEMBERS = {
    "bundle.yaml",
    "strategy.dsl.yaml",
    "market-profile.yaml",
    "parameters.yaml",
    "risk-envelope.yaml",
    "lineage.yaml",
    "evidence/summary.yaml",
    "conformance/bars.csv",
    "conformance/expected_weights.yaml",
}


def _load_yaml(data: bytes, label: str) -> Any:
    try:
        doc = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise ImportRejected(f"invalid YAML in {label}: {exc}") from exc
    if doc is None:
        raise ImportRejected(f"empty YAML in {label}")
    _reject_secret_keys(doc, label)
    return doc


def _reject_secret_keys(doc: Any, label: str) -> None:
    if isinstance(doc, dict):
        for key, value in doc.items():
            lower = str(key).lower()
            if any(fragment in lower for fragment in _SECRET_FRAGMENTS):
                raise ImportRejected(f"secret-like key in {label}: {key}")
            _reject_secret_keys(value, label)
    elif isinstance(doc, list):
        for value in doc:
            _reject_secret_keys(value, label)


@dataclass(frozen=True)
class BundleManifest:
    schema_version: str
    dsl_version: str
    bundle_id: str
    content_hash: str
    created_at: str
    registry_uri: str | None


@dataclass(frozen=True)
class MarketProfile:
    id: str
    calendar: str
    benchmark: str


@dataclass(frozen=True)
class Lineage:
    run_id: str
    candidate_id: str
    research_outcome: str
    engine_hash: str
    data_snapshot_hash: str


@dataclass(frozen=True)
class EvidenceSummary:
    passes_all: bool
    gates: list[str]


@dataclass(frozen=True)
class StrategyDsl:
    dsl_version: str
    universe: list[str]
    steps: list[dict]


@dataclass(frozen=True)
class ConformanceExpected:
    effective_at: str
    weights: dict[str, float]


def load_bundle_manifest(data: bytes) -> BundleManifest:
    doc = _load_yaml(data, "bundle.yaml")
    if not isinstance(doc, dict):
        raise ImportRejected("bundle.yaml must be a mapping")
    try:
        manifest = BundleManifest(
            schema_version=str(doc["schema_version"]),
            dsl_version=str(doc["dsl_version"]),
            bundle_id=str(doc["bundle_id"]),
            content_hash=str(doc["content_hash"]),
            created_at=str(doc["created_at"]),
            registry_uri=doc.get("registry_uri"),
        )
    except KeyError as exc:
        raise ImportRejected(f"missing field in bundle.yaml: {exc.args[0]}") from exc
    if (manifest.schema_version, manifest.dsl_version) not in SUPPORTED:
        raise ImportRejected(
            f"unsupported version pair: {manifest.schema_version}, {manifest.dsl_version}"
        )
    return manifest


def load_market_profile(data: bytes) -> MarketProfile:
    doc = _load_yaml(data, "market-profile.yaml")
    if not isinstance(doc, dict):
        raise ImportRejected("market-profile.yaml must be a mapping")
    try:
        profile = MarketProfile(
            id=str(doc["id"]),
            calendar=str(doc["calendar"]),
            benchmark=str(doc["benchmark"]),
        )
    except KeyError as exc:
        raise ImportRejected(f"missing field in market-profile.yaml: {exc.args[0]}") from exc
    if profile.id != "us-equity-daily":
        raise ImportRejected(f"unsupported market profile id: {profile.id}; only us-equity-daily")
    return profile


def load_lineage(data: bytes) -> Lineage:
    doc = _load_yaml(data, "lineage.yaml")
    if not isinstance(doc, dict):
        raise ImportRejected("lineage.yaml must be a mapping")
    if "research_outcome" in doc and str(doc["research_outcome"]) != "FOUND":
        raise ImportRejected(
            f"research_outcome must be FOUND, got {doc['research_outcome']!r}"
        )
    try:
        lineage = Lineage(
            run_id=str(doc["run_id"]),
            candidate_id=str(doc["candidate_id"]),
            research_outcome=str(doc["research_outcome"]),
            engine_hash=str(doc["engine_hash"]),
            data_snapshot_hash=str(doc["data_snapshot_hash"]),
        )
    except KeyError as exc:
        raise ImportRejected(f"missing field in lineage.yaml: {exc.args[0]}") from exc
    if lineage.research_outcome != "FOUND":
        raise ImportRejected(
            f"research_outcome must be FOUND, got {lineage.research_outcome!r}"
        )
    return lineage


def load_evidence_summary(data: bytes) -> EvidenceSummary:
    doc = _load_yaml(data, "evidence/summary.yaml")
    if not isinstance(doc, dict):
        raise ImportRejected("evidence/summary.yaml must be a mapping")
    if "passes_all" in doc and not bool(doc["passes_all"]):
        raise ImportRejected("evidence/summary.yaml passes_all must be true")
    try:
        summary = EvidenceSummary(
            passes_all=bool(doc["passes_all"]),
            gates=[str(g) for g in doc["gates"]],
        )
    except KeyError as exc:
        raise ImportRejected(f"missing field in evidence/summary.yaml: {exc.args[0]}") from exc
    if not summary.passes_all:
        raise ImportRejected("evidence/summary.yaml passes_all must be true")
    return summary


def load_parameters(data: bytes) -> dict:
    doc = _load_yaml(data, "parameters.yaml")
    if not isinstance(doc, dict):
        raise ImportRejected("parameters.yaml must be a JSON-compatible mapping")
    return doc


def load_risk_envelope(data: bytes) -> dict:
    doc = _load_yaml(data, "risk-envelope.yaml")
    if not isinstance(doc, dict):
        raise ImportRejected("risk-envelope.yaml must be a mapping")
    from alphastrategy.risk.policy import AccountPolicy, merge_limits

    merge_limits(doc, AccountPolicy.defaults(), None)
    return doc


def load_strategy_dsl(data: bytes) -> StrategyDsl:
    doc = _load_yaml(data, "strategy.dsl.yaml")
    if not isinstance(doc, dict):
        raise ImportRejected("strategy.dsl.yaml must be a mapping")
    try:
        return StrategyDsl(
            dsl_version=str(doc["dsl_version"]),
            universe=[str(s) for s in doc["universe"]],
            steps=list(doc["steps"]),
        )
    except KeyError as exc:
        raise ImportRejected(f"missing field in strategy.dsl.yaml: {exc.args[0]}") from exc


def load_conformance_expected(data: bytes) -> ConformanceExpected:
    doc = _load_yaml(data, "conformance/expected_weights.yaml")
    if not isinstance(doc, dict):
        raise ImportRejected("conformance/expected_weights.yaml must be a mapping")
    try:
        return ConformanceExpected(
            effective_at=str(doc["effective_at"]),
            weights={str(k): float(v) for k, v in doc["weights"].items()},
        )
    except KeyError as exc:
        raise ImportRejected(
            f"missing field in conformance/expected_weights.yaml: {exc.args[0]}"
        ) from exc


def require_members(members: dict[str, bytes]) -> None:
    missing = sorted(_REQUIRED_MEMBERS - set(members))
    if missing:
        raise ImportRejected(f"missing required members: {', '.join(missing)}")
    if not any(name.startswith("conformance/") for name in members):
        raise ImportRejected("missing conformance/ members")
