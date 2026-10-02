from __future__ import annotations

import requests

from src.api.api_client import ApiClient


class SalesAPI:
    def __init__(self, client: ApiClient) -> None:
        self._client = client

    def create(self, payload: dict) -> requests.Response:
        return self._client.post("/sales", json=payload)

    def get(self, sale_id: int) -> requests.Response:
        return self._client.get(f"/sales/{sale_id}")
