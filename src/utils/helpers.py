"""Funções auxiliares sem estado, compartilhadas entre testes e camadas."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from config.settings import PROJECT_ROOT

TEST_DATA_DIR = PROJECT_ROOT / "test_data"


def load_test_data(filename: str) -> Any:
    """Carrega um JSON de test_data/. Usável em tempo de coleta (parametrize)."""
    path: Path = TEST_DATA_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))


def parse_brl(text: str) -> Decimal:
    """'R$ 1.234,56' -> Decimal('1234.56')."""
    cleaned = text.replace("R$", "").replace("\xa0", "").strip()
    return Decimal(cleaned.replace(".", "").replace(",", "."))


def money(value: float | int | str | Decimal) -> Decimal:
    """Converte para Decimal via str, evitando ruído de float (0.1 + 0.2)."""
    return Decimal(str(value))


def assert_schema(instance: Any, schema: dict) -> None:
    """Valida `instance` contra um JSON Schema com mensagem de falha legível."""
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        details = "; ".join(f"{'/'.join(map(str, e.path)) or '<raiz>'}: {e.message}" for e in errors)
        raise AssertionError(f"JSON fora do schema: {details}\nPayload: {instance!r}")


def as_params(cases: list[dict]) -> list:
    """Transforma casos do JSON ({'id': ..., ...}) em pytest.param com id legível."""
    return [pytest.param(case, id=case["id"]) for case in cases]
