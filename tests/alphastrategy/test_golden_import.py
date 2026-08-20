import json
from pathlib import Path

from alphastrategy.bundle.import_bundle import import_asb
from alphastrategy.home import AlphaStrategyHome

GOLDEN_ASB = Path(__file__).parent / "fixtures" / "golden.asb"


def _home(tmp_path: Path) -> AlphaStrategyHome:
    return AlphaStrategyHome.from_env({"ALPHASTRATEGY_HOME": str(tmp_path / "home")})


def test_import_golden_asb_records_imported_state(tmp_path: Path):
    assert GOLDEN_ASB.is_file(), "golden.asb fixture must be checked in"
    home = _home(tmp_path)
    bundle_id = import_asb(GOLDEN_ASB, home)

    assert bundle_id.startswith("asb_")
    bundle_dir = home.bundle_dir(bundle_id)
    assert bundle_dir.is_dir()
    assert bundle_dir.parent == home.imported_dir()
    assert (bundle_dir / "strategy.dsl.yaml").is_file()
    assert (bundle_dir / "conformance" / "bars.csv").is_file()

    meta_path = bundle_dir / "import-meta.json"
    assert meta_path.is_file()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "imported_at" in meta
    assert meta["source_path"] == str(GOLDEN_ASB.resolve())
