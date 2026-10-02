from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SaleItem:
    product_id: int
    quantity: int

    def to_payload(self) -> dict:
        return {"product_id": self.product_id, "quantity": self.quantity}
