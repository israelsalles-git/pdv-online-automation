"""Fixtures e hooks compartilhados por toda a suíte (API, UI e fiscal)."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pytest_html import extras

from config.settings import ConfigurationError, Settings, load_settings
from src.api.api_client import ApiClient
from src.api.auth_api import AuthAPI
from src.api.customers_api import CustomersAPI
from src.api.products_api import ProductsAPI
from src.api.sales_api import SalesAPI
from src.models import Customer, Product
from src.pages.customers_page import CustomersPage
from src.pages.dashboard_page import DashboardPage
from src.pages.login_page import LoginPage
from src.pages.products_page import ProductsPage
from src.pages.sales_page import SalesPage
from src.utils.demo_server import DemoServer, is_up
from src.utils.driver_factory import create_driver
from src.utils.helpers import load_test_data
from src.utils.logger import get_logger

log = get_logger("pytest")


# --------------------------------------------------------------------------- hooks

def pytest_configure(config: pytest.Config) -> None:
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        raise pytest.UsageError(str(exc)) from exc
    settings.screenshots_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)


def pytest_html_report_title(report) -> None:
    report.title = "PDV Online Automation - Relatório de Testes"


def pytest_runtest_logstart(nodeid: str, location) -> None:
    log.info("INÍCIO %s", nodeid)


def _save_screenshot(item: pytest.Item, settings: Settings) -> tuple[Path, str] | None:
    driver = item.funcargs.get("driver")
    if driver is None:
        return None
    safe_name = re.sub(r"[^\w.-]+", "_", item.name).strip("_")
    path = settings.screenshots_dir / f"{safe_name}_{datetime.now():%Y-%m-%d_%H%M%S}.png"
    try:
        path.write_bytes(driver.get_screenshot_as_png())
        encoded = driver.get_screenshot_as_base64()
    except Exception:  # o navegador pode ter morrido; não pode mascarar a falha original
        log.exception("Não foi possível capturar screenshot de %s", item.nodeid)
        return None
    log.error("Screenshot da falha salvo em %s", path)
    return path, encoded


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" or (report.when == "setup" and not report.passed):
        log.info("FIM %s -> %s", item.nodeid, report.outcome.upper())
    if report.failed and report.when in ("setup", "call"):
        log.error("Falha em %s (%s):\n%s", item.nodeid, report.when, report.longreprtext)
        shot = _save_screenshot(item, load_settings())
        if shot:
            report.extras = [*getattr(report, "extras", []), extras.png(shot[1], name=shot[0].name)]


# --------------------------------------------------------------------------- configuração e dados

@pytest.fixture(scope="session")
def settings() -> Settings:
    return load_settings()


@pytest.fixture(scope="session")
def demo_server(settings: Settings):
    """Garante um sistema respondendo em BASE_URL: reutiliza o existente ou sobe o demo_app."""
    if is_up(settings.base_url):
        log.info("Usando sistema já em execução em %s", settings.base_url)
        yield
        return
    if not settings.start_demo_app:
        raise RuntimeError(f"Nada responde em {settings.base_url}/health e START_DEMO_APP=false")
    server = DemoServer(settings.base_url, settings.username, settings.password)
    server.start()
    try:
        yield
    finally:
        server.stop()


@pytest.fixture(scope="session")
def base_url(settings: Settings, demo_server) -> str:
    return settings.base_url


@pytest.fixture(scope="session")
def api_url(settings: Settings, demo_server) -> str:
    return settings.api_url


@pytest.fixture(scope="session")
def users_data() -> dict:
    return load_test_data("users.json")


@pytest.fixture(scope="session")
def products_data() -> dict:
    return load_test_data("products.json")


@pytest.fixture(scope="session")
def nfce_dir(settings: Settings) -> Path:
    return settings.test_data_dir / "nfce"


# --------------------------------------------------------------------------- API

@pytest.fixture
def anonymous_client(api_url: str, settings: Settings):
    client = ApiClient(api_url, settings.timeout)
    yield client
    client.close()


@pytest.fixture
def auth_api(anonymous_client: ApiClient) -> AuthAPI:
    return AuthAPI(anonymous_client)


@pytest.fixture(scope="session")
def api_client(api_url: str, settings: Settings):
    client = ApiClient(api_url, settings.timeout)
    AuthAPI(client).authenticate(settings.username, settings.password)
    yield client
    client.close()


@pytest.fixture(scope="session")
def products_api(api_client: ApiClient) -> ProductsAPI:
    return ProductsAPI(api_client)


@pytest.fixture(scope="session")
def customers_api(api_client: ApiClient) -> CustomersAPI:
    return CustomersAPI(api_client)


@pytest.fixture(scope="session")
def sales_api(api_client: ApiClient) -> SalesAPI:
    return SalesAPI(api_client)


@pytest.fixture
def created_product(products_api: ProductsAPI):
    """Produto criado via API para o teste, removido ao final (setup rápido e isolado)."""
    response = products_api.create(Product.build(name="Produto de Teste", price=Decimal("19.90")).to_payload())
    assert response.status_code == 201, response.text
    product = response.json()
    yield product
    products_api.delete(product["id"])


@pytest.fixture
def created_customer(customers_api: CustomersAPI) -> dict:
    response = customers_api.create(Customer.build().to_payload())
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------- UI

@pytest.fixture
def driver(settings: Settings, demo_server):
    """Um navegador por teste; sempre encerrado, mesmo quando o teste falha."""
    web_driver = create_driver(settings.browser, settings.headless)
    try:
        yield web_driver
    finally:
        web_driver.quit()


@pytest.fixture
def login_page(driver, settings: Settings) -> LoginPage:
    return LoginPage(driver, settings.base_url, settings.timeout)


@pytest.fixture
def dashboard_page(driver, settings: Settings) -> DashboardPage:
    return DashboardPage(driver, settings.base_url, settings.timeout)


@pytest.fixture
def logged_in(login_page: LoginPage, dashboard_page: DashboardPage, settings: Settings) -> None:
    login_page.open()
    login_page.login(settings.username, settings.password)
    assert dashboard_page.is_loaded(), "Login de pré-condição falhou: dashboard não carregou"


@pytest.fixture
def products_page(driver, settings: Settings, logged_in) -> ProductsPage:
    return ProductsPage(driver, settings.base_url, settings.timeout)


@pytest.fixture
def customers_page(driver, settings: Settings, logged_in) -> CustomersPage:
    return CustomersPage(driver, settings.base_url, settings.timeout)


@pytest.fixture
def sales_page(driver, settings: Settings, logged_in) -> SalesPage:
    return SalesPage(driver, settings.base_url, settings.timeout)
