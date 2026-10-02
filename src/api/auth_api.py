from __future__ import annotations

import requests

from src.api.api_client import ApiClient


class AuthAPI:
    def __init__(self, client: ApiClient) -> None:
        self._client = client

    def login(self, payload: dict) -> requests.Response:
        return self._client.post("/login", json=payload)

    def authenticate(self, username: str, password: str) -> str:
        """Faz login e configura o token no cliente; falha se as credenciais forem recusadas."""
        response = self.login({"username": username, "password": password})
        response.raise_for_status()
        token = response.json()["token"]
        self._client.set_token(token)
        return token
