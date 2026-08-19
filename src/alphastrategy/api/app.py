from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from alphastrategy.api.handlers import _apply_startup_runtime, dispatch
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.supervisor.loop import Supervisor


class _ApiContext:
    def __init__(self, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
        self.home = home
        self.supervisor = supervisor


class AlphaStrategyHandler(BaseHTTPRequestHandler):
    server: ThreadingHTTPServer  # type: ignore[assignment]

    def log_message(self, format: str, *args: Any) -> None:
        return None

    def do_GET(self) -> None:
        self._dispatch()

    def do_POST(self) -> None:
        self._dispatch()

    def do_PUT(self) -> None:
        self._dispatch()

    def _dispatch(self) -> None:
        context = self.server.api_context
        path = self.path.split("?", 1)[0]
        dispatch(self, context.home, context.supervisor, self.command, path)


def make_server(
    home: AlphaStrategyHome,
    supervisor: Supervisor,
    bind: str = "127.0.0.1",
    port: int = 7460,
) -> ThreadingHTTPServer:
    _apply_startup_runtime(home, supervisor)
    server = ThreadingHTTPServer((bind, port), AlphaStrategyHandler)
    server.api_context = _ApiContext(home, supervisor)
    return server
