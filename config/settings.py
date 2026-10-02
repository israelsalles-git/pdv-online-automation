"""Configuração centralizada, lida de variáveis de ambiente (e do arquivo .env)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")  # variáveis já definidas no ambiente (ex.: CI) têm prioridade


class ConfigurationError(RuntimeError):
    """Variável de ambiente obrigatória ausente ou inválida."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"Variável de ambiente {name} não definida. Copie .env.example para .env e preencha."
        )
    return value


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_url: str
    username: str
    password: str
    browser: str
    headless: bool
    timeout: int
    start_demo_app: bool
    log_level: str
    reports_dir: Path = PROJECT_ROOT / "reports"
    screenshots_dir: Path = PROJECT_ROOT / "reports" / "screenshots"
    logs_dir: Path = PROJECT_ROOT / "logs"
    test_data_dir: Path = PROJECT_ROOT / "test_data"


def load_settings() -> Settings:
    base_url = _required("BASE_URL").rstrip("/")
    api_url = os.getenv("API_URL", "").strip().rstrip("/") or f"{base_url}/api"
    return Settings(
        base_url=base_url,
        api_url=api_url,
        username=_required("TEST_USERNAME"),
        password=_required("TEST_PASSWORD"),
        browser=os.getenv("BROWSER", "chrome").strip().lower(),
        headless=_as_bool("HEADLESS", True),
        timeout=int(os.getenv("TIMEOUT", "10")),
        start_demo_app=_as_bool("START_DEMO_APP", True),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
    )
