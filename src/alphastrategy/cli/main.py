"""alphastrategy CLI entry point."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from alphastrategy.api.app import make_server
from alphastrategy.bundle.import_bundle import import_asb
from alphastrategy.errors import ImportRejected
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.dsl.sandbox import run_sandbox
from alphastrategy.live.alpaca import AlpacaAdapter
from alphastrategy.live.broker import CONFIRM_LIVE_FLAG
from alphastrategy.risk.policy import AccountPolicy
from alphastrategy.supervisor import audit
from alphastrategy.supervisor.loop import Supervisor
from alphastrategy.supervisor.state import SupervisorState

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7460

_FORBIDDEN_LIVE_FLAGS = frozenset(
    {
        "--live",
        f"--{CONFIRM_LIVE_FLAG}",
        "--confirm-yes-i-know-what-im-doing",
    }
)


def _reject_live_flags(argv: list[str]) -> int | None:
    for arg in argv:
        if arg in _FORBIDDEN_LIVE_FLAGS or arg.startswith("--live"):
            print(
                "error: v1 CLI does not support live trading; paper mode only",
                file=sys.stderr,
            )
            return 1
    return None


def _home() -> AlphaStrategyHome:
    home = AlphaStrategyHome.from_env()
    home.root.mkdir(parents=True, exist_ok=True)
    return home


def _validate_start_host(host: str) -> int | None:
    if host == "0.0.0.0":
        print("error: binding to 0.0.0.0 is not allowed in v1", file=sys.stderr)
        return 1
    if host != DEFAULT_HOST:
        print(f"error: only {DEFAULT_HOST} is allowed in v1", file=sys.stderr)
        return 1
    return None


def _make_paper_broker() -> AlpacaAdapter:
    return AlpacaAdapter(
        api_key=os.environ.get("ALPACA_API_KEY") or os.environ.get("APCA_API_KEY_ID"),
        secret=os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY"),
        paper=True,
        confirm_live=False,
    )


def _bars_dict_from_broker(broker: Any, symbols: list[str]) -> dict[str, Any]:
    end = datetime.now(timezone.utc).date().isoformat()
    start = (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat()
    raw = broker.get_bars(sorted(symbols), start, end)
    dates: list[str] = []
    cols: dict[str, list[float]] = {symbol: [] for symbol in symbols}
    for symbol in symbols:
        sym_data = raw.get(symbol, {})
        bars = sym_data.get("bars", []) if isinstance(sym_data, dict) else []
        for index, bar in enumerate(bars):
            if not isinstance(bar, dict):
                continue
            timestamp = bar.get("t") or bar.get("timestamp")
            date_str = str(timestamp)[:10] if timestamp else f"day{index}"
            if index == len(dates):
                dates.append(date_str)
            cols[symbol].append(float(bar.get("c", 0.0)))
    if not dates:
        dates = [end]
        for symbol in symbols:
            if not cols[symbol]:
                cols[symbol] = [100.0]
    return {"date": dates, **cols}


def _bundle_universe(bundle_dir: Path) -> list[str]:
    dsl = yaml.safe_load((bundle_dir / "strategy.dsl.yaml").read_bytes())
    return list(dsl.get("universe", []))


def _bundle_effective_at(bundle_dir: Path) -> str:
    path = bundle_dir / "conformance" / "expected_weights.yaml"
    if path.is_file():
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and doc.get("effective_at"):
            return str(doc["effective_at"])
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _make_weight_fn(home: AlphaStrategyHome, broker: Any) -> Callable[[str], dict[str, float]]:
    def weight_fn(bundle_id: str) -> dict[str, float]:
        bundle_dir = home.bundle_dir(bundle_id)
        symbols = _bundle_universe(bundle_dir)
        bars = _bars_dict_from_broker(broker, symbols)
        effective_at = _bundle_effective_at(bundle_dir)
        return run_sandbox(bundle_dir, bars, effective_at)

    return weight_fn


def _make_supervisor(home: AlphaStrategyHome, broker: Any) -> Supervisor:
    return Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        weight_fn=_make_weight_fn(home, broker),
    )


def _cmd_import(home: AlphaStrategyHome, path: Path) -> int:
    try:
        bundle_id = import_asb(path, home)
        audit.append(home.audit_path(), {"event": "import", "bundle_id": bundle_id})
        print(bundle_id)
        return 0
    except ImportRejected as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _cmd_start(home: AlphaStrategyHome, broker: Any, host: str, port: int) -> int:
    supervisor = _make_supervisor(home, broker)
    server = make_server(home, supervisor, bind=host, port=port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


def _cmd_status(home: AlphaStrategyHome, broker: Any) -> int:
    supervisor = _make_supervisor(home, broker)
    snapshot = supervisor.snapshot
    try:
        clock = broker.get_clock()
    except Exception as exc:
        clock = {"error": str(exc)}
    halted = snapshot.state == SupervisorState.HALTED
    payload = {
        "state": snapshot.state.value,
        "clock": clock,
        "halted": halted,
        "halt_reason": snapshot.halt_reason,
    }
    print(json.dumps(payload, separators=(",", ":")))
    return 0


def _cmd_paper_start(home: AlphaStrategyHome, broker: Any, bundle_id: str, allocation: float) -> int:
    supervisor = _make_supervisor(home, broker)
    try:
        supervisor.start_sleeve(bundle_id, allocation)
        return 0
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _cmd_paper_stop(home: AlphaStrategyHome, broker: Any, bundle_id: str) -> int:
    supervisor = _make_supervisor(home, broker)
    supervisor.stop_sleeve(bundle_id)
    return 0


def _cmd_paper_kill(home: AlphaStrategyHome, broker: Any, bundle_id: str | None) -> int:
    supervisor = _make_supervisor(home, broker)
    if bundle_id:
        supervisor.kill_sleeve(bundle_id)
    else:
        supervisor.kill_account()
    return 0


def _cmd_paper_resume(home: AlphaStrategyHome, broker: Any) -> int:
    supervisor = _make_supervisor(home, broker)
    supervisor.resume()
    return 0


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alphastrategy",
        description="AlphaStrategy paper trading control plane",
    )
    subparsers = parser.add_subparsers(dest="command")

    import_parser = subparsers.add_parser("import", help="import a strategy bundle (.asb)")
    import_parser.add_argument("file", type=Path, help="path to .asb file")

    start_parser = subparsers.add_parser("start", help="start control plane HTTP server")
    start_parser.add_argument("--host", default=DEFAULT_HOST, help="bind host (v1: localhost only)")
    start_parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="bind port")

    subparsers.add_parser("status", help="show supervisor status")

    paper_parser = subparsers.add_parser("paper", help="paper trading controls")
    paper_sub = paper_parser.add_subparsers(dest="paper_command")

    paper_start = paper_sub.add_parser("start", help="start paper sleeve")
    paper_start.add_argument("--bundle", required=True, help="bundle id")
    paper_start.add_argument("--allocation", type=float, required=True, help="allocation 0-1")

    paper_stop = paper_sub.add_parser("stop", help="stop paper sleeve")
    paper_stop.add_argument("--bundle", required=True, help="bundle id")

    paper_kill = paper_sub.add_parser("kill", help="kill sleeve or account")
    paper_kill.add_argument("--bundle", default=None, help="bundle id (omit for account kill)")

    paper_sub.add_parser("resume", help="resume from halt")

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    live_rc = _reject_live_flags(argv)
    if live_rc is not None:
        return live_rc

    parser = create_parser()
    if not argv:
        parser.print_help()
        return 1

    args = parser.parse_args(argv)
    home = _home()

    if args.command == "import":
        return _cmd_import(home, args.file)

    if args.command == "start":
        host_rc = _validate_start_host(args.host)
        if host_rc is not None:
            return host_rc

    needs_broker = args.command in {"start", "status", "paper"}
    broker: Any | None = None
    if needs_broker:
        broker = _make_paper_broker()

    if args.command == "start":
        return _cmd_start(home, broker, args.host, args.port)

    if args.command == "status":
        return _cmd_status(home, broker)

    if args.command == "paper":
        if args.paper_command == "start":
            return _cmd_paper_start(home, broker, args.bundle, args.allocation)
        if args.paper_command == "stop":
            return _cmd_paper_stop(home, broker, args.bundle)
        if args.paper_command == "kill":
            return _cmd_paper_kill(home, broker, args.bundle)
        if args.paper_command == "resume":
            return _cmd_paper_resume(home, broker)
        parser.error("paper subcommand required")

    parser.print_help()
    return 1
