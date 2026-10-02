import pytest

from src.api import schemas
from src.api.products_api import ProductsAPI
from src.utils.helpers import as_params, assert_schema, load_test_data

pytestmark = [pytest.mark.api, pytest.mark.regression]

USERS = load_test_data("users.json")


@pytest.mark.smoke
def test_login_with_valid_credentials(auth_api, settings):
    response = auth_api.login({"username": settings.username, "password": settings.password})

    assert response.status_code == 200
    body = response.json()
    assert_schema(body, schemas.LOGIN)
    assert body["user"]["username"] == settings.username


@pytest.mark.parametrize("case", as_params(USERS["wrong_passwords"]))
def test_login_with_wrong_password(auth_api, settings, case):
    response = auth_api.login({"username": settings.username, "password": case["password"]})

    assert response.status_code == 401
    assert_schema(response.json(), schemas.ERROR)
    assert response.json()["error"] == "Usuário ou senha inválidos"
    assert "token" not in response.json()


@pytest.mark.parametrize("case", as_params(USERS["unknown_users"]))
def test_login_with_unknown_user(auth_api, settings, case):
    response = auth_api.login({"username": case["username"], "password": settings.password})

    assert response.status_code == 401
    assert response.json()["error"] == "Usuário ou senha inválidos"


@pytest.mark.parametrize("case", as_params(USERS["missing_fields"]))
def test_login_with_missing_fields(auth_api, case):
    response = auth_api.login(case["payload"])

    assert response.status_code == 400
    assert_schema(response.json(), schemas.ERROR)
    assert response.json()["error"] == "Informe usuário e senha"


def test_protected_endpoint_rejects_missing_token(anonymous_client):
    response = ProductsAPI(anonymous_client).list()

    assert response.status_code == 401
    assert_schema(response.json(), schemas.ERROR)


def test_protected_endpoint_rejects_invalid_token(anonymous_client):
    anonymous_client.set_token("token-invalido")

    response = ProductsAPI(anonymous_client).list()

    assert response.status_code == 401
