from pathlib import Path

import pytest

from alphastrategy.errors import ImportRejected
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.bundle.import_bundle import import_asb
from tests.alphastrategy.fixtures.make_asb import (
    build_golden_asb,
    mutate_member,
    mutate_member_rehash,
)


def _home(tmp_path: Path) -> AlphaStrategyHome:
    return AlphaStrategyHome.from_env({"ALPHASTRATEGY_HOME": str(tmp_path / "home")})


def test_import_rejects_hash_mismatch(tmp_path: Path):
    raw = build_golden_asb()
    broken = mutate_member(raw, "strategy.dsl.yaml", b"steps: []\n")
    dest = tmp_path / "bad.asb"
    dest.write_bytes(broken)
    home = _home(tmp_path)
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected as e:
        assert "hash" in str(e).lower()


def test_import_rejects_not_found_outcome(tmp_path: Path):
    raw = mutate_member(build_golden_asb(), "lineage.yaml", b"research_outcome: NO_EVIDENCE\n")
    dest = tmp_path / "nofound.asb"
    dest.write_bytes(raw)
    home = _home(tmp_path)
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected as e:
        assert "FOUND" in str(e)


def test_import_rejects_passes_all_false(tmp_path: Path):
    raw = mutate_member(
        build_golden_asb(),
        "evidence/summary.yaml",
        b"passes_all: false\ngates: [dsr]\n",
    )
    dest = tmp_path / "failgates.asb"
    dest.write_bytes(raw)
    home = _home(tmp_path)
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected as e:
        assert "passes_all" in str(e).lower()


def test_import_rejects_market_profile_id(tmp_path: Path):
    raw = mutate_member(
        build_golden_asb(),
        "market-profile.yaml",
        b"id: eu-equity-daily\ncalendar: LSE\nbenchmark: FTSE\n",
    )
    dest = tmp_path / "badmarket.asb"
    dest.write_bytes(raw)
    home = _home(tmp_path)
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected as e:
        assert "us-equity-daily" in str(e)


def test_import_rejects_unsupported_schema_version(tmp_path: Path):
    raw = build_golden_asb()
    broken = mutate_member(
        raw,
        "bundle.yaml",
        b"schema_version: alphastrategy.bundle/v99\n"
        b"dsl_version: alphaloop.dsl/v0\n"
        b"bundle_id: asb_deadbeef\n"
        b"content_hash: deadbeef\n"
        b"created_at: '2026-08-19T00:00:00Z'\n"
        b"registry_uri: null\n",
    )
    dest = tmp_path / "badschema.asb"
    dest.write_bytes(broken)
    home = _home(tmp_path)
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected as e:
        msg = str(e).lower()
        assert "schema" in msg or "unsupported" in msg or "version" in msg


def test_import_rejects_secret_like_key_in_bundle_yaml(tmp_path: Path):
    raw = build_golden_asb()
    broken = mutate_member(
        raw,
        "bundle.yaml",
        b"schema_version: alphastrategy.bundle/v0\n"
        b"dsl_version: alphaloop.dsl/v0\n"
        b"api_key: sk-secret\n"
        b"bundle_id: asb_deadbeef\n"
        b"content_hash: deadbeef\n"
        b"created_at: '2026-08-19T00:00:00Z'\n"
        b"registry_uri: null\n",
    )
    dest = tmp_path / "secret.asb"
    dest.write_bytes(broken)
    home = _home(tmp_path)
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected as e:
        msg = str(e).lower()
        assert "api_key" in msg or "secret" in msg


@pytest.mark.parametrize(
    ("member", "contents", "secret_key"),
    [
        ("parameters.yaml", b"model:\n  access_token: forbidden\n", "access_token"),
        (
            "parameters.yaml",
            b"model:\n  broker_credential: forbidden\n",
            "broker_credential",
        ),
        (
            "lineage.yaml",
            b"run_id: run-1\ncandidate_id: c-1\nresearch_outcome: FOUND\n"
            b"engine_hash: engine\npassword_hint: forbidden\n"
            b"data_snapshot_hash: data\n",
            "password_hint",
        ),
        (
            "risk-envelope.yaml",
            b"max_gross: 1.0\nbroker_key_name: forbidden\n",
            "broker_key_name",
        ),
        (
            "evidence/summary.yaml",
            b"passes_all: true\ngates: [dsr]\nsecret_note: forbidden\n",
            "secret_note",
        ),
    ],
)
def test_import_rejects_secret_like_keys_in_all_yaml_mappings(
    tmp_path: Path,
    member: str,
    contents: bytes,
    secret_key: str,
):
    broken = mutate_member_rehash(build_golden_asb(), member, contents)
    dest = tmp_path / "secret.asb"
    dest.write_bytes(broken)

    with pytest.raises(ImportRejected, match="secret-like key") as exc:
        import_asb(dest, _home(tmp_path))

    assert secret_key in str(exc.value)


def test_import_rejects_dsl_version_mismatch_with_manifest(tmp_path: Path):
    broken = mutate_member_rehash(
        build_golden_asb(),
        "strategy.dsl.yaml",
        b"dsl_version: alphaloop.dsl/v99\n"
        b"universe: [AAPL, MSFT]\n"
        b"steps:\n  - op: equal_weight\n",
    )
    dest = tmp_path / "dsl-mismatch.asb"
    dest.write_bytes(broken)

    with pytest.raises(ImportRejected, match="dsl_version"):
        import_asb(dest, _home(tmp_path))


@pytest.mark.parametrize(
    "risk_envelope",
    [
        b"unknown_cap: 0.1\n",
        b"max_gross: -0.1\n",
        b"max_name_weight: .nan\n",
    ],
)
def test_import_rejects_invalid_risk_envelope(tmp_path: Path, risk_envelope: bytes):
    broken = mutate_member_rehash(
        build_golden_asb(),
        "risk-envelope.yaml",
        risk_envelope,
    )
    dest = tmp_path / "invalid-risk.asb"
    dest.write_bytes(broken)

    with pytest.raises(ImportRejected):
        import_asb(dest, _home(tmp_path))


def test_import_rejects_missing_conformance_members(tmp_path: Path):
    raw = build_golden_asb()
    buf_in = __import__("io").BytesIO(raw)
    out = __import__("io").BytesIO()
    import zipfile

    with zipfile.ZipFile(buf_in) as zin, zipfile.ZipFile(out, "w") as zout:
        for item in zin.infolist():
            if not item.filename.startswith("conformance/"):
                zout.writestr(item.filename, zin.read(item.filename))
    dest = tmp_path / "noconf.asb"
    dest.write_bytes(out.getvalue())
    home = _home(tmp_path)
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected as e:
        assert "conformance" in str(e).lower()


def test_import_succeeds_for_golden(tmp_path: Path):
    dest = tmp_path / "golden.asb"
    dest.write_bytes(build_golden_asb())
    home = _home(tmp_path)
    bundle_id = import_asb(dest, home)
    assert bundle_id.startswith("asb_")
    bundle_dir = home.bundle_dir(bundle_id)
    assert (bundle_dir / "strategy.dsl.yaml").is_file()
    assert (bundle_dir / "conformance" / "bars.csv").is_file()
    assert (bundle_dir / "import-meta.json").is_file()
