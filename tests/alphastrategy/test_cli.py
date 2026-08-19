from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from alphastrategy.cli.main import main
from alphastrategy.home import AlphaStrategyHome

GOLDEN_ASB = Path(__file__).parent / "fixtures" / "golden.asb"


class FakeBroker:
    def __init__(self) -> None:
        self._is_open = False

    def get_account(self) -> dict:
        return {"equity": "10000", "cash": "10000"}

    def list_positions(self) -> list[dict]:
        return []

    def place_order(self, symbol: str, qty: float, side: str) -> dict:
        return {"id": "order-1", "status": "filled"}

    def cancel_order(self, order_id: str) -> None:
        return None

    def close_all(self) -> None:
        return None

    def get_clock(self) -> dict:
        return {
            "is_open": self._is_open,
            "next_open": "2024-01-31T14:30:00",
            "next_close": "2024-01-31T21:00:00",
            "timestamp": "2024-01-31T14:30:00",
        }

    def get_bars(self, symbols: list[str], start: str, end: str) -> dict:
        return {symbol: {"bars": [{"c": 100.0, "t": "2024-01-31"}]} for symbol in symbols}


@pytest.fixture
def cli_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home_root = tmp_path / "home"
    monkeypatch.setenv("ALPHASTRATEGY_HOME", str(home_root))
    return home_root


@pytest.fixture
def fake_broker() -> FakeBroker:
    return FakeBroker()


@pytest.fixture
def patch_alpaca(fake_broker: FakeBroker):
    with mock.patch("alphastrategy.cli.main.AlpacaAdapter") as adapter_cls:
        adapter_cls.return_value = fake_broker
        yield adapter_cls


def test_cli_import_golden_asb(cli_home: Path) -> None:
    assert GOLDEN_ASB.is_file()
    rc = main(["import", str(GOLDEN_ASB)])
    assert rc == 0

    home = AlphaStrategyHome.from_env()
    imported = list(cli_home.joinpath("imported").iterdir())
    assert len(imported) == 1
    bundle_id = imported[0].name
    assert bundle_id.startswith("asb_")
    assert (home.bundle_dir(bundle_id) / "strategy.dsl.yaml").is_file()


def test_paper_start_rejects_live_flag(cli_home: Path, patch_alpaca: mock.MagicMock) -> None:
    rc = main(
        [
            "paper",
            "start",
            "--bundle",
            "asb_test",
            "--allocation",
            "0.5",
            "--live",
        ]
    )
    assert rc != 0
    patch_alpaca.assert_not_called()


def test_paper_start_rejects_confirm_live_flag(cli_home: Path, patch_alpaca: mock.MagicMock) -> None:
    rc = main(
        [
            "paper",
            "start",
            "--bundle",
            "asb_test",
            "--allocation",
            "0.5",
            "--confirm-yes-i-know-what-im-doing",
        ]
    )
    assert rc != 0
    patch_alpaca.assert_not_called()


def test_start_rejects_live_flag(patch_alpaca: mock.MagicMock) -> None:
    rc = main(["start", "--live"])
    assert rc != 0
    patch_alpaca.assert_not_called()


def test_start_rejects_public_bind(patch_alpaca: mock.MagicMock) -> None:
    rc = main(["start", "--host", "0.0.0.0"])
    assert rc != 0
    patch_alpaca.assert_not_called()


def test_start_starts_supervisor_heartbeat(cli_home: Path, patch_alpaca: mock.MagicMock) -> None:
    with mock.patch("alphastrategy.cli.main.make_server") as make_server:
        with mock.patch("alphastrategy.cli.main.start_heartbeat") as start_heartbeat:
            server = mock.MagicMock()
            server.serve_forever.side_effect = KeyboardInterrupt
            make_server.return_value = server

            rc = main(["start"])

    assert rc == 0
    start_heartbeat.assert_called_once()
    supervisor = start_heartbeat.call_args.args[0]
    assert supervisor is make_server.call_args.args[1]


def test_start_uses_paper_adapter(cli_home: Path, patch_alpaca: mock.MagicMock) -> None:
    with mock.patch("alphastrategy.cli.main.make_server") as make_server:
        server = mock.MagicMock()
        server.serve_forever.side_effect = KeyboardInterrupt
        make_server.return_value = server

        with mock.patch.dict(
            os.environ,
            {"ALPACA_API_KEY": "PK_TEST", "ALPACA_API_SECRET_KEY": "SECRET_TEST"},
            clear=False,
        ):
            rc = main(["start"])

    assert rc == 0
    patch_alpaca.assert_called_once()
    kwargs = patch_alpaca.call_args.kwargs
    assert kwargs.get("paper", True) is True
    assert kwargs.get("confirm_live", False) is False
    make_server.assert_called_once()
    bind = make_server.call_args.kwargs.get("bind") or make_server.call_args.args[2]
    assert bind == "127.0.0.1"


def test_paper_start_persists_allocation(cli_home: Path, patch_alpaca: mock.MagicMock) -> None:
    rc = main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"])
    assert rc == 0

    state = json.loads((cli_home / "supervisor-state.json").read_text(encoding="utf-8"))
    assert state["sleeves"]["asb_test"] == 0.25
    patch_alpaca.assert_called_once()


def test_status_prints_json(cli_home: Path, patch_alpaca: mock.MagicMock, capsys) -> None:
    main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"])

    rc = main(["status"])
    assert rc == 0

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["state"] == "idle_out_of_session"
    assert "clock" in payload
    assert payload["halted"] is False
