import pytest

from src.utils.helpers import as_params, load_test_data

pytestmark = [pytest.mark.ui, pytest.mark.regression]

USERS = load_test_data("users.json")


@pytest.mark.smoke
def test_login_success(login_page, dashboard_page, settings):
    login_page.open()

    login_page.login(settings.username, settings.password)

    assert dashboard_page.is_loaded()
    assert settings.username in dashboard_page.get_welcome_message()


@pytest.mark.parametrize("case", as_params(USERS["wrong_passwords"]))
def test_login_invalid_password(login_page, dashboard_page, settings, case):
    login_page.open()

    login_page.login(settings.username, case["password"])

    assert login_page.get_error_message() == "Usuário ou senha inválidos"
    assert not dashboard_page.is_loaded()


@pytest.mark.parametrize("case", as_params(USERS["unknown_users"]))
def test_login_unknown_user(login_page, settings, case):
    login_page.open()

    login_page.login(case["username"], settings.password)

    assert login_page.get_error_message() == "Usuário ou senha inválidos"


@pytest.mark.parametrize(
    "username, password",
    [("", ""), ("usuario", ""), ("", "senha")],
    ids=["both_empty", "no_password", "no_username"],
)
def test_login_requires_both_fields(login_page, username, password):
    login_page.open()

    login_page.login(username, password)

    assert login_page.get_error_message() == "Informe usuário e senha"


def test_protected_page_redirects_anonymous_user_to_login(login_page, dashboard_page):
    dashboard_page.open()

    assert login_page.is_loaded()


@pytest.mark.smoke
def test_logout_returns_to_login(login_page, dashboard_page, settings):
    login_page.open()
    login_page.login(settings.username, settings.password)

    dashboard_page.logout()

    assert login_page.is_loaded()
    dashboard_page.open()
    assert login_page.is_loaded(), "sessão deveria ter sido encerrada"
