"""Cliente HTTP reutilizável: sessão, timeout, autenticação e logging de cada chamada."""
from __future__ import annotations

import requests

from src.utils.logger import get_logger

log = get_logger("api")


class ApiClient:
    def __init__(self, base_url: str, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def set_token(self, token: str | None) -> None:
        if token:
            self._session.headers["Authorization"] = f"Bearer {token}"
        else:
            self._session.headers.pop("Authorization", None)

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        log.info("%s %s", method, url)
        try:
            response = self._session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException:
            log.exception("Falha de transporte em %s %s", method, url)
            raise
        log.info("<- %s %s (%.0f ms)", response.status_code, url, response.elapsed.total_seconds() * 1000)
        if not response.ok:
            log.warning("Resposta de erro: %s", response.text[:300])
        return response

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, json: dict | None = None, **kwargs) -> requests.Response:
        return self.request("POST", path, json=json, **kwargs)

    def put(self, path: str, json: dict | None = None, **kwargs) -> requests.Response:
        return self.request("PUT", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)

    def close(self) -> None:
        self._session.close()
