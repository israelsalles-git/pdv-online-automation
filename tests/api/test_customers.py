import pytest

from src.api import schemas
from src.models import Customer
from src.utils.helpers import assert_schema

pytestmark = [pytest.mark.api, pytest.mark.regression]


@pytest.mark.smoke
def test_list_customers(customers_api):
    response = customers_api.list()

    assert response.status_code == 200
    body = response.json()
    assert_schema(body, schemas.list_of(schemas.CUSTOMER))
    assert "Maria Silva" in [c["name"] for c in body]


@pytest.mark.smoke
def test_create_customer(customers_api):
    customer = Customer.build()

    response = customers_api.create(customer.to_payload())

    assert response.status_code == 201
    body = response.json()
    assert_schema(body, schemas.CUSTOMER)
    assert (body["name"], body["email"]) == (customer.name, customer.email)


def test_get_customer_by_id(customers_api, created_customer):
    response = customers_api.get(created_customer["id"])

    assert response.status_code == 200
    assert response.json() == created_customer


def test_get_unknown_customer_returns_404(customers_api):
    response = customers_api.get(999_999)

    assert response.status_code == 404
    assert_schema(response.json(), schemas.ERROR)


def test_search_customers_by_name(customers_api, created_customer):
    response = customers_api.list(search=created_customer["name"])

    assert response.status_code == 200
    assert [c["id"] for c in response.json()] == [created_customer["id"]]


@pytest.mark.parametrize("name", [None, "", "   "], ids=["missing", "empty", "blank"])
def test_create_customer_without_name(customers_api, name):
    payload = {"document": "000.000.000-00", "email": "x@example.com"}
    if name is not None:
        payload["name"] = name

    response = customers_api.create(payload)

    assert response.status_code == 400
    assert response.json()["error"] == "Nome é obrigatório"


@pytest.mark.parametrize("email", ["sem-arroba", "a@b", "@example.com"])
def test_create_customer_with_invalid_email(customers_api, email):
    response = customers_api.create({"name": "Cliente E-mail", "email": email})

    assert response.status_code == 400
    assert response.json()["error"] == "E-mail inválido"
