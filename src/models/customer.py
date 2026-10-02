from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass
class Customer:
    name: str
    document: str = ""
    email: str = ""

    @classmethod
    def build(cls, **overrides) -> "Customer":
        suffix = uuid4().hex[:6]
        data = {"name": f"Cliente Teste {suffix}", "document": "000.000.000-00", "email": f"cliente.{suffix}@example.com"}
        data.update(overrides)
        return cls(**data)

    def to_payload(self) -> dict:
        return {"name": self.name, "document": self.document, "email": self.email}
