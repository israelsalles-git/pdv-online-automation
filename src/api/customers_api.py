from __future__ import annotations

import requests

from src.api.api_client import ApiClient


class CustomersAPI:
    def __init__(self, client: ApiClient) -> None:
        self._client = client

    def list(self, search: str | None = None) -> requests.Response:
        params = {"search": search} if search else None
        return self._client.get("/customers", params=params)

    def get(self, customer_id: int) -> requests.Response:
        return self._client.get(f"/customers/{customer_id}")

    def create(self, payload: dict) -> requests.Response:
        return self._client.post("/customers", json=payload)
