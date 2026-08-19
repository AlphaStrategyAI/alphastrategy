from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from alphastrategy.api.handlers import _apply_startup_runtime, dispatch
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.supervisor.loop import Supervisor

_STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"

_STATIC_ROUTES: dict[str, str] = {
    "/": "index.html",
    "/index.html": "index.html",
    "/styles.css": "styles.css",
    "/app.js": "app.js",
    "/static/styles.css": "styles.css",
    "/static/app.js": "app.js",
}

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}

HEARTBEAT_INTERVAL_SEC = 20


class _ApiContext:
    def __init__(self, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
        self.home = home
        self.supervisor = supervisor


def _serve_static(handler: BaseHTTPRequestHandler, path: str) -> bool:
    filename = _STATIC_ROUTES.get(path)
    if filename is None:
        return False
    file_path = _STATIC_DIR / filename
    if not file_path.is_file():
        return False
    body = file_path.read_bytes()
    content_type = _CONTENT_TYPES.get(file_path.suffix, "application/octet-stream")
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
    return True


def start_heartbeat(
    supervisor: Supervisor,
    interval: float = HEARTBEAT_INTERVAL_SEC,
) -> threading.Thread:
    def _loop() -> None:
        while True:
            supervisor.tick()
            time.sleep(interval)

    thread = threading.Thread(target=_loop, name="supervisor-heartbeat", daemon=True)
    thread.start()
    return thread


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
        path = self.path.split("?", 1)[0]
        if self.command == "GET" and _serve_static(self, path):
            return
        context = self.server.api_context
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
