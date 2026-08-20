from pathlib import Path
from alphastrategy.home import AlphaStrategyHome

def test_home_uses_env_override(tmp_path: Path):
    home = AlphaStrategyHome.from_env({"ALPHASTRATEGY_HOME": str(tmp_path)})
    assert home.root == tmp_path
    assert home.bundle_dir("asb_abc") == tmp_path / "imported" / "asb_abc"

