from __future__ import annotations

import json
import os
import threading
from datetime import date
from pathlib import Path
from unittest import mock

import pytest

from alphastrategy.api.app import make_server
from alphastrategy.cli.main import _make_weight_fn, _shutdown_flatten, main
from alphastrategy.errors import HaltRequested
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.risk.policy import AccountPolicy
from alphastrategy.supervisor.loop import Supervisor
from alphastrategy.supervisor.state import SupervisorState

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

    def cancel_open_orders(self) -> None:
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


def _create_imported_bundle(home_root: Path, bundle_id: str = "asb_test") -> Path:
    bundle_dir = home_root / "imported" / bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)
    return bundle_dir


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


def test_cli_import_rejected_prints_kind(cli_home: Path, tmp_path: Path, capsys) -> None:
    from tests.alphastrategy.fixtures.make_asb import build_golden_asb, mutate_member

    dest = tmp_path / "tampered.asb"
    dest.write_bytes(mutate_member(build_golden_asb(), "strategy.dsl.yaml", b"steps: []\n"))
    rc = main(["import", str(dest)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "hash" in err.lower()
    assert "Re-export" in err


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
    calls = []
    with mock.patch("alphastrategy.cli.main.make_server") as make_server:
        with mock.patch("alphastrategy.cli.main.start_heartbeat") as start_heartbeat:
            with mock.patch("alphastrategy.cli.main.signal.signal") as signal_install:
                server = mock.MagicMock()
                server.serve_forever.side_effect = KeyboardInterrupt
                make_server.return_value = server
                make_server.side_effect = lambda *args, **kwargs: calls.append("server") or server
                start_heartbeat.side_effect = lambda *args, **kwargs: calls.append("heartbeat")
                signal_install.side_effect = lambda _signum, handler: (
                    calls.append("handler")
                    if getattr(handler, "__name__", "") == "_interrupt"
                    else None
                )

                rc = main(["start"])

    assert rc == 0
    start_heartbeat.assert_called_once()
    supervisor = start_heartbeat.call_args.args[0]
    assert supervisor is make_server.call_args.args[1]
    assert calls == ["server", "handler", "handler", "heartbeat"]


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
    _create_imported_bundle(cli_home)
    rc = main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"])
    assert rc == 0

    state = json.loads((cli_home / "supervisor-state.json").read_text(encoding="utf-8"))
    assert state["sleeves"]["asb_test"] == 0.25
    patch_alpaca.assert_not_called()


def test_status_prints_json(cli_home: Path, patch_alpaca: mock.MagicMock, capsys) -> None:
    _create_imported_bundle(cli_home)
    main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"])

    rc = main(["status"])
    assert rc == 0

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["state"] == "idle_out_of_session"
    assert "clock" in payload
    assert payload["halted"] is False
    assert payload["flattened"] is False
    assert "last_rebalance_event" in payload
    assert "last_rebalance_complete" in payload
    assert "last_kill" in payload
    assert payload["last_kill"] is None
    assert "utilization" in payload
    assert payload["utilization"]["orders_today"] == 0
    assert payload["utilization"]["cash_weight"] is None
    assert "heartbeat" in payload
    assert payload["heartbeat"]["interval_seconds"] == 20
    assert payload["book"]["source"] == "none"


def test_status_prints_limit_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    from alphastrategy.supervisor.state import load_state, save_state

    _create_imported_bundle(cli_home)
    main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"])
    home = AlphaStrategyHome.from_env()
    snap = load_state(home.state_path())
    snap.last_got = {"AAPL": 0.225}
    save_state(home.state_path(), snap)
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert payload["utilization"]["live_limit"]["reason"] == "max_name_weight"
    err = captured.err
    assert "LIMIT:" in err
    assert "Name cap" in err
    assert "next rebalance will flatten" in err.lower()
    patch_alpaca.assert_not_called()


def test_status_prints_book_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "idle_in_session",
        "clock": {},
        "halted": False,
        "flattened": False,
        "utilization": {},
        "heartbeat": {"age_seconds": 4, "pulse": "live", "interval_seconds": 20},
        "book": {"source": "heartbeat"},
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    out = json.loads(captured.out.strip())
    assert out["book"]["source"] == "heartbeat"
    assert captured.err.splitlines() == ["BOOK: heartbeat"]
    patch_alpaca.assert_not_called()


def test_status_prints_pnl_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "idle_in_session",
        "clock": {},
        "halted": False,
        "flattened": False,
        "utilization": {"live_limit": {"reason": "max_name_weight"}},
        "heartbeat": {"age_seconds": 4, "pulse": "live", "interval_seconds": 20},
        "book": {"source": "heartbeat"},
        "pnl": 100.0,
        "pnl_source": "last_close",
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    out = json.loads(captured.out.strip())
    assert out["pnl"] == 100.0
    assert captured.err.splitlines() == [
        "BOOK: heartbeat",
        "PNL: 100.00 vs last close",
        "LIMIT: live book through Name cap — next rebalance will flatten",
    ]
    patch_alpaca.assert_not_called()


def test_status_prints_send_limit_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "idle_in_session",
        "clock": {},
        "halted": False,
        "flattened": False,
        "utilization": {
            "live_limit": {"reason": "max_order_notional_frac", "kind": "send"}
        },
        "heartbeat": {"age_seconds": 4, "pulse": "live", "interval_seconds": 20},
        "book": {"source": "heartbeat"},
        "pnl": 100.0,
        "pnl_source": "last_close",
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "BOOK: heartbeat",
        "PNL: 100.00 vs last close",
        "LIMIT: next send through Order size — next rebalance will flatten",
    ]
    patch_alpaca.assert_not_called()


def test_status_prints_unknown_limit_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "idle_in_session",
        "clock": {},
        "halted": False,
        "flattened": False,
        "utilization": {
            "live_limit": {"reason": "next_send_unknown", "kind": "unknown"}
        },
        "heartbeat": {"age_seconds": 4, "pulse": "live", "interval_seconds": 20},
        "book": {"source": "heartbeat"},
        "pnl": 100.0,
        "pnl_source": "last_close",
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    out = json.loads(captured.out.strip())
    assert out["pnl"] == 100.0
    assert captured.err.splitlines() == [
        "BOOK: heartbeat",
        "PNL: 100.00 vs last close",
        "LIMIT: next send waits for last sleeve weights — Caps cannot dry-run",
    ]
    patch_alpaca.assert_not_called()


def test_status_prints_seed_halt_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "halted",
        "clock": {},
        "halted": True,
        "halt_reason": "start paper seeds last sleeve weights: no evaluator for sleeve asb_z",
        "flattened": False,
        "utilization": {},
        "book": {"source": "glance"},
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "BOOK: glance",
        "HALT: start paper that cannot seed last weights holds",
    ]
    patch_alpaca.assert_not_called()


def test_status_prints_halt_reason_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "halted",
        "clock": {},
        "halted": True,
        "halt_reason": "stale bars",
        "flattened": False,
        "utilization": {},
        "book": {"source": "glance"},
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "BOOK: glance",
        "HALT: stale bars",
    ]
    patch_alpaca.assert_not_called()


def test_status_prints_resume_seed_halt_on_stderr(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "halted",
        "clock": {},
        "halted": True,
        "halt_reason": "no evaluator for sleeve asb_z",
        "flattened": False,
        "utilization": {},
        "book": {"source": "glance"},
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "BOOK: glance",
        "HALT: resume does not seed last weights",
    ]
    patch_alpaca.assert_not_called()


def test_status_omits_pnl_when_null(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "state": "idle_in_session",
        "clock": {},
        "halted": False,
        "flattened": False,
        "utilization": {},
        "book": {"source": "glance"},
        "pnl": None,
        "pnl_source": None,
    }
    monkeypatch.setattr(
        "alphastrategy.cli.main._control_request",
        lambda *args, **kwargs: (200, payload),
    )
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err.splitlines() == ["BOOK: glance"]
    patch_alpaca.assert_not_called()


def test_status_omits_limit_when_flattened(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    from alphastrategy.supervisor.state import load_state, save_state

    _create_imported_bundle(cli_home)
    main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"])
    home = AlphaStrategyHome.from_env()
    snap = load_state(home.state_path())
    snap.last_got = {"AAPL": 0.225}
    snap.state = SupervisorState.STOPPED
    save_state(home.state_path(), snap)
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    json.loads(captured.out.strip())
    assert "LIMIT:" not in captured.err
    patch_alpaca.assert_not_called()


def test_weight_fn_uses_last_fetched_bar_and_long_lookback(tmp_path: Path) -> None:
    home = AlphaStrategyHome(root=tmp_path)
    bundle_dir = home.bundle_dir("asb_test")
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "strategy.dsl.yaml").write_text(
        "dsl_version: alphaloop.dsl/v0\n"
        "universe: [AAPL]\n"
        "steps:\n"
        "  - op: equal_weight\n",
        encoding="utf-8",
    )
    (bundle_dir / "conformance").mkdir()
    (bundle_dir / "conformance" / "expected_weights.yaml").write_text(
        "effective_at: '1999-01-01T00:00:00Z'\nweights: {AAPL: 1.0}\n",
        encoding="utf-8",
    )

    class BarsBroker:
        request: tuple[str, str] | None = None

        def get_bars(self, symbols, start, end):
            self.request = (start, end)
            return {
                "AAPL": {
                    "bars": [
                        {"c": 90.0, "t": "2026-08-17T20:00:00Z"},
                        {"c": 100.0, "t": "2026-08-18T20:00:00Z"},
                    ]
                }
            }

    broker = BarsBroker()
    with mock.patch("alphastrategy.cli.main.run_sandbox", return_value={"AAPL": 1.0}) as run:
        weights = _make_weight_fn(home, broker)("asb_test")

    assert weights == {"AAPL": 1.0}
    assert run.call_args.args[2] == "2026-08-18T20:00:00Z"
    assert broker.request is not None
    start, end = broker.request
    assert (date.fromisoformat(end) - date.fromisoformat(start)).days >= 400


def test_weight_fn_halts_on_empty_broker_bars(tmp_path: Path) -> None:
    home = AlphaStrategyHome(root=tmp_path)
    bundle_dir = home.bundle_dir("asb_test")
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "strategy.dsl.yaml").write_text(
        "dsl_version: alphaloop.dsl/v0\n"
        "universe: [AAPL]\n"
        "steps:\n"
        "  - op: equal_weight\n",
        encoding="utf-8",
    )

    class EmptyBarsBroker:
        def get_bars(self, symbols, start, end):
            return {"AAPL": {"bars": []}}

    with pytest.raises(HaltRequested, match="missing bars"):
        _make_weight_fn(home, EmptyBarsBroker())("asb_test")


def test_shutdown_flatten_kills_account_before_server_shutdown() -> None:
    supervisor = mock.MagicMock()
    server = mock.MagicMock()
    calls = []
    supervisor.kill_account.side_effect = lambda: calls.append("kill")
    server.shutdown.side_effect = lambda: calls.append("shutdown")

    _shutdown_flatten(supervisor, server)

    assert calls == ["kill", "shutdown"]


def test_paper_start_uses_running_control_plane_without_constructing_alpaca(
    cli_home: Path,
    patch_alpaca: mock.MagicMock,
) -> None:
    _create_imported_bundle(cli_home)
    home = AlphaStrategyHome(root=cli_home)
    broker = FakeBroker()
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        rc = main(
            [
                "paper",
                "start",
                "--bundle",
                "asb_test",
                "--allocation",
                "0.25",
                "--port",
                str(server.server_port),
            ]
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert rc == 0
    assert supervisor.snapshot.sleeves["asb_test"] == 0.25
    patch_alpaca.assert_not_called()


def test_help_command_prints_operator_copy(cli_home: Path, capsys) -> None:
    rc = main(["help"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "halt is not flatten" in out.lower()
    assert "FLATTEN" in out
    assert "--force" in out
    assert "sole order placer" in out.lower()


def test_help_command_does_not_construct_alpaca(
    cli_home: Path, patch_alpaca: mock.MagicMock
) -> None:
    rc = main(["help"])
    assert rc == 0
    patch_alpaca.assert_not_called()


def test_top_level_help_epilog_points_to_help_command(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "halt is not flatten" in out.lower()
    assert "alphastrategy help" in out


def test_paper_kill_help_mentions_flatten(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["paper", "kill", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "flatten" in out
    assert "halt" in out


def test_paper_resume_help_mentions_no_catch_up(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["paper", "resume", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "catch up" in out or "catch-up" in out


def test_paper_stop_help_mentions_next_rebalance(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["paper", "stop", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "rebalance" in out


def test_paper_start_help_mentions_halted_waits(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["paper", "start", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "halt" in out
    assert "resume" in out


def test_paper_start_while_halted_prints_held(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    _create_imported_bundle(cli_home)
    home = AlphaStrategyHome.from_env()
    supervisor = Supervisor(
        home=home,
        broker=FakeBroker(),
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.start_sleeve("asb_test", 0.25)
    supervisor._halt("stale bars")
    assert supervisor.state == SupervisorState.HALTED
    rc = main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.3"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "held:" in err.lower()
    assert "resume" in err.lower()
    assert "catch up" in err.lower()


def test_paper_start_seed_failure_prints_seed_hold(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    home = AlphaStrategyHome.from_env()
    home.bundle_dir("asb_z").mkdir(parents=True, exist_ok=True)
    supervisor = Supervisor(
        home=home,
        broker=FakeBroker(),
        policy=AccountPolicy.defaults(),
        evaluators={},
    )
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        rc = main(
            [
                "paper",
                "start",
                "--bundle",
                "asb_z",
                "--allocation",
                "0.18",
                "--port",
                str(server.server_port),
            ]
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
    assert rc == 0
    err = capsys.readouterr().err.lower()
    assert "held:" in err
    assert "cannot seed last weights holds" in err
    assert "catch up" in err
    assert "flattened:" not in err


def test_paper_start_overlay_breach_prints_flattened(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    import yaml

    bundle_dir = _create_imported_bundle(cli_home)
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")
    home = AlphaStrategyHome.from_env()
    home.runtime_path().write_text(
        yaml.safe_dump({"sleeve_overlays": {"asb_test": {"max_name_weight": 0.05}}}),
        encoding="utf-8",
    )
    broker = FakeBroker()
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.snapshot.last_got = {"AAPL": 0.15}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor._persist()
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        rc = main(
            [
                "paper",
                "start",
                "--bundle",
                "asb_test",
                "--allocation",
                "0.25",
                "--port",
                str(server.server_port),
            ]
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    err = captured.err.lower()
    assert "flattened:" in err
    assert "sleeve overlay" in err
    assert "flattens now" in err
    patch_alpaca.assert_not_called()


def test_paper_kill_prints_outcome_json(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    _create_imported_bundle(cli_home, "asb_test")
    home = AlphaStrategyHome.from_env()
    broker = FakeBroker()
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.start_sleeve("asb_test", 0.25)
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        rc = main(
            [
                "paper",
                "kill",
                "--bundle",
                "asb_test",
                "--port",
                str(server.server_port),
            ]
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["reason"] == "fallback_not_ready"
    assert payload["flattened"] is True
    assert payload["isolated"] is False


def test_paper_kill_help_mentions_force(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["paper", "kill", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "--force" in out
    assert "tty" in out


def test_cli_account_kill_without_force_on_non_tty_does_not_flatten(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    _create_imported_bundle(cli_home)
    assert main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"]) == 0
    rc = main(["paper", "kill"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "pass --force" in err
    state = json.loads((cli_home / "supervisor-state.json").read_text(encoding="utf-8"))
    assert state["sleeves"]["asb_test"] == 0.25
    patch_alpaca.assert_not_called()


def test_cli_account_kill_with_force_prints_account_outcome(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    _create_imported_bundle(cli_home)
    assert main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"]) == 0
    rc = main(["paper", "kill", "--force"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["reason"] == "account"
    assert payload["flattened"] is True
    assert payload["isolated"] is False
    assert payload["scope"] == "account"


def test_cli_account_kill_tty_flatten_without_force(
    cli_home: Path, patch_alpaca: mock.MagicMock, monkeypatch, capsys
) -> None:
    from io import StringIO

    from alphastrategy.cli import confirm as confirm_mod

    _create_imported_bundle(cli_home)
    assert main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"]) == 0

    stdin = StringIO("FLATTEN\n")
    stderr = StringIO()

    def _tty_confirm(*, force: bool, **_kwargs):
        return confirm_mod.confirm_account_kill(
            force=force, stdin=stdin, stderr=stderr, isatty=lambda: True
        )

    monkeypatch.setattr("alphastrategy.cli.main.confirm_account_kill", _tty_confirm)
    rc = main(["paper", "kill"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["reason"] == "account"
    assert "Type FLATTEN" in stderr.getvalue()


def test_cli_account_kill_tty_wrong_phrase_does_not_flatten(
    cli_home: Path, patch_alpaca: mock.MagicMock, monkeypatch, capsys
) -> None:
    from io import StringIO

    from alphastrategy.cli import confirm as confirm_mod

    _create_imported_bundle(cli_home)
    assert main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"]) == 0

    stdin = StringIO("yes\n")
    stderr = StringIO()

    def _tty_confirm(*, force: bool, **_kwargs):
        return confirm_mod.confirm_account_kill(
            force=force, stdin=stdin, stderr=stderr, isatty=lambda: True
        )

    monkeypatch.setattr("alphastrategy.cli.main.confirm_account_kill", _tty_confirm)
    rc = main(["paper", "kill"])
    assert rc == 1
    state = json.loads((cli_home / "supervisor-state.json").read_text(encoding="utf-8"))
    assert state["sleeves"]["asb_test"] == 0.25
    patch_alpaca.assert_not_called()


def test_cli_account_kill_control_plane_without_force_does_not_post(
    cli_home: Path, patch_alpaca: mock.MagicMock
) -> None:
    _create_imported_bundle(cli_home, "asb_test")
    home = AlphaStrategyHome.from_env()
    broker = FakeBroker()
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.start_sleeve("asb_test", 0.25)
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        rc = main(["paper", "kill", "--port", str(server.server_port)])
    finally:
        server.shutdown()
        thread.join(timeout=2)
    assert rc == 1
    assert supervisor.snapshot.sleeves["asb_test"] == 0.25
    assert supervisor.snapshot.last_kill is None


def test_cli_account_kill_control_plane_with_force_flattens(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    _create_imported_bundle(cli_home, "asb_test")
    home = AlphaStrategyHome.from_env()
    broker = FakeBroker()
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_test": {"AAPL": 1.0}},
    )
    supervisor.start_sleeve("asb_test", 0.25)
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        rc = main(
            ["paper", "kill", "--force", "--port", str(server.server_port)]
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["reason"] == "account"
    assert supervisor.snapshot.last_kill["reason"] == "account"


def test_offline_status_includes_last_kill_after_account_kill(
    cli_home: Path, patch_alpaca: mock.MagicMock, capsys
) -> None:
    _create_imported_bundle(cli_home)
    assert main(["paper", "start", "--bundle", "asb_test", "--allocation", "0.25"]) == 0
    assert main(["paper", "kill", "--force"]) == 0
    capsys.readouterr()
    rc = main(["status"])
    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert payload["last_kill"]["reason"] == "account"
    assert payload["last_kill"]["flattened"] is True
    assert payload["pnl"] is None
    assert payload["pnl_source"] is None
    assert "PNL:" not in captured.err

