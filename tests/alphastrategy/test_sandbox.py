import subprocess
from pathlib import Path
from unittest import mock

import yaml

from alphastrategy.bundle.import_bundle import import_asb
from alphastrategy.dsl.sandbox import run_sandbox, weights_match
from alphastrategy.errors import HaltRequested, ImportRejected
from alphastrategy.home import AlphaStrategyHome
from tests.alphastrategy.fixtures.make_asb import (
    build_golden_asb,
    mutate_member_rehash,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "golden"


def _unpack_golden(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    for p in FIXTURE_DIR.rglob("*"):
        if p.is_file():
            rel = p.relative_to(FIXTURE_DIR)
            dest = bundle_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(p.read_bytes())
    return bundle_dir


def _bars_payload() -> dict:
    return {
        "date": ["2024-01-30", "2024-01-31"],
        "AAPL": [100.0, 101.0],
        "MSFT": [200.0, 201.0],
    }


def _home(tmp_path: Path) -> AlphaStrategyHome:
    return AlphaStrategyHome.from_env({"ALPHASTRATEGY_HOME": str(tmp_path / "home")})


def test_weights_match_exact_and_tolerance():
    assert weights_match({"AAPL": 0.5, "MSFT": 0.5}, {"AAPL": 0.5, "MSFT": 0.5})
    tol_ok = 0.5 + max(1e-9, 0.5 * 1e-6) * 0.5
    assert weights_match({"AAPL": tol_ok, "MSFT": 0.5}, {"AAPL": 0.5, "MSFT": 0.5})
    assert not weights_match({"AAPL": 0.5 + 1e-5, "MSFT": 0.5}, {"AAPL": 0.5, "MSFT": 0.5})
    assert not weights_match({"AAPL": 0.5}, {"AAPL": 0.5, "MSFT": 0.5})


def test_worker_returns_expected_weights(tmp_path: Path):
    bundle_dir = _unpack_golden(tmp_path)
    weights = run_sandbox(bundle_dir, _bars_payload(), "2024-01-31")
    assert weights == {"AAPL": 0.5, "MSFT": 0.5}


def test_timeout_raises_halt_requested(tmp_path: Path):
    bundle_dir = _unpack_golden(tmp_path)
    with mock.patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="worker", timeout=0.01),
    ):
        try:
            run_sandbox(bundle_dir, _bars_payload(), "2024-01-31", timeout_s=0.01)
            assert False, "should have halted"
        except HaltRequested:
            pass


def test_import_rejects_conformance_weights_off(tmp_path: Path):
    bad_expected = yaml.safe_dump(
        {"effective_at": "2024-01-31", "weights": {"AAPL": 0.50001, "MSFT": 0.49999}}
    ).encode()
    raw = mutate_member_rehash(
        build_golden_asb(), "conformance/expected_weights.yaml", bad_expected
    )
    dest = tmp_path / "off.asb"
    dest.write_bytes(raw)
    home = _home(tmp_path)
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected as e:
        assert "conformance" in str(e).lower()


def test_import_rejects_extra_asset_in_expected(tmp_path: Path):
    extra = yaml.safe_dump(
        {
            "effective_at": "2024-01-31",
            "weights": {"AAPL": 0.5, "MSFT": 0.5, "GOOG": 0.0},
        }
    ).encode()
    raw = mutate_member_rehash(
        build_golden_asb(), "conformance/expected_weights.yaml", extra
    )
    dest = tmp_path / "extra.asb"
    dest.write_bytes(raw)
    home = _home(tmp_path)
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected as e:
        assert "conformance" in str(e).lower()


def test_import_staging_removed_on_conformance_failure(tmp_path: Path):
    bad_expected = yaml.safe_dump(
        {"effective_at": "2024-01-31", "weights": {"AAPL": 0.6, "MSFT": 0.4}}
    ).encode()
    raw = mutate_member_rehash(
        build_golden_asb(), "conformance/expected_weights.yaml", bad_expected
    )
    dest = tmp_path / "staging.asb"
    dest.write_bytes(raw)
    home = _home(tmp_path)
    try:
        import_asb(dest, home)
        assert False, "should have rejected"
    except ImportRejected:
        pass
    imported = home.imported_dir()
    assert not any(imported.iterdir()) if imported.exists() else True


def test_import_succeeds_golden_after_conformance_gate(tmp_path: Path):
    dest = tmp_path / "golden.asb"
    dest.write_bytes(build_golden_asb())
    home = _home(tmp_path)
    bundle_id = import_asb(dest, home)
    assert bundle_id.startswith("asb_")
    assert (home.bundle_dir(bundle_id) / "strategy.dsl.yaml").is_file()
