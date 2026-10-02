from __future__ import annotations

import requests

from src.api.api_client import ApiClient


class ProductsAPI:
    def __init__(self, client: ApiClient) -> None:
        self._client = client

    def list(self, search: str | None = None) -> requests.Response:
        params = {"search": search} if search else None
        return self._client.get("/products", params=params)

    def get(self, product_id: int) -> requests.Response:
        return self._client.get(f"/products/{product_id}")

    def create(self, payload: dict) -> requests.Response:
        return self._client.post("/products", json=payload)

    def update(self, product_id: int, payload: dict) -> requests.Response:
        return self._client.put(f"/products/{product_id}", json=payload)

    def delete(self, product_id: int) -> requests.Response:
        return self._client.delete(f"/products/{product_id}")
