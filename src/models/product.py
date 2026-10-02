from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4


@dataclass
class Product:
    code: str
    name: str
    price: Decimal
    ncm: str = ""

    @classmethod
    def build(cls, **overrides) -> "Product":
        """Produto válido com código único (evita colisão entre execuções)."""
        data = {
            "code": f"T{uuid4().hex[:8].upper()}",
            "name": "Produto de Teste",
            "price": Decimal("10.00"),
            "ncm": "00000000",  # NCM fictício, apenas demonstrativo
        }
        data.update(overrides)
        data["price"] = Decimal(str(data["price"]))
        return cls(**data)

    def to_payload(self) -> dict:
        return {"code": self.code, "name": self.name, "price": float(self.price), "ncm": self.ncm}
