"""Sobe o demo_app em uma thread para a execução local/CI dos testes."""
from __future__ import annotations

import threading
from urllib.parse import urlparse

import requests
from werkzeug.serving import make_server

from demo_app.app import create_app
from src.utils.logger import get_logger

log = get_logger("demo_server")


def is_up(base_url: str) -> bool:
    try:
        return requests.get(f"{base_url}/health", timeout=1).ok
    except requests.RequestException:
        return False


class DemoServer:
    def __init__(self, base_url: str, username: str, password: str) -> None:
        parsed = urlparse(base_url)
        self._server = make_server(
            parsed.hostname or "127.0.0.1", parsed.port or 80,
            create_app(username, password), threaded=True,
        )
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()
        log.info("demo_app iniciado em %s:%s", *self._server.server_address[:2])

    def stop(self) -> None:
        self._server.shutdown()
        self._thread.join(timeout=5)
        log.info("demo_app encerrado")
