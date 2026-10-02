import pytest

from src.api import schemas
from src.models import Product
from src.utils.helpers import as_params, assert_schema, load_test_data

pytestmark = [pytest.mark.api, pytest.mark.regression]

PRODUCTS = load_test_data("products.json")


@pytest.mark.smoke
def test_list_products_returns_seeded_catalog(products_api):
    response = products_api.list()

    assert response.status_code == 200
    body = response.json()
    assert_schema(body, schemas.list_of(schemas.PRODUCT))
    by_code = {p["code"]: p for p in body}
    for expected in PRODUCTS["seeded_products"]:
        assert by_code[expected["code"]]["name"] == expected["name"]
        assert by_code[expected["code"]]["price"] == pytest.approx(expected["price"])


@pytest.mark.smoke
def test_create_product(products_api):
    product = Product.build(name="Macarrão 500g", price="6.75")

    response = products_api.create(product.to_payload())

    assert response.status_code == 201
    body = response.json()
    assert_schema(body, schemas.PRODUCT)
    assert (body["code"], body["name"], body["price"]) == (product.code, "Macarrão 500g", 6.75)
    products_api.delete(body["id"])


def test_get_product_by_id(products_api, created_product):
    response = products_api.get(created_product["id"])

    assert response.status_code == 200
    assert_schema(response.json(), schemas.PRODUCT)
    assert response.json() == created_product


def test_get_unknown_product_returns_404(products_api):
    response = products_api.get(999_999)

    assert response.status_code == 404
    assert_schema(response.json(), schemas.ERROR)


def test_update_product(products_api, created_product):
    payload = {**created_product, "name": "Produto Atualizado", "price": 21.5}

    response = products_api.update(created_product["id"], payload)

    assert response.status_code == 200
    assert response.json()["name"] == "Produto Atualizado"
    assert response.json()["price"] == 21.5
    assert products_api.get(created_product["id"]).json()["name"] == "Produto Atualizado"


def test_delete_product(products_api):
    product_id = products_api.create(Product.build().to_payload()).json()["id"]

    response = products_api.delete(product_id)

    assert response.status_code == 204
    assert products_api.get(product_id).status_code == 404


def test_delete_unknown_product_returns_404(products_api):
    assert products_api.delete(999_999).status_code == 404


@pytest.mark.parametrize("case", as_params(PRODUCTS["invalid_products"]))
def test_create_product_with_invalid_data(products_api, case):
    response = products_api.create(case["payload"])

    assert response.status_code == 400
    assert_schema(response.json(), schemas.ERROR)
    assert case["error"] in response.json()["error"].lower()


def test_create_product_with_duplicate_code(products_api, created_product):
    duplicate = Product.build(code=created_product["code"])

    response = products_api.create(duplicate.to_payload())

    assert response.status_code == 409
    assert response.json()["error"] == "Código já cadastrado"


def test_search_products_by_name(products_api, created_product):
    response = products_api.list(search=created_product["code"])

    assert response.status_code == 200
    assert [p["id"] for p in response.json()] == [created_product["id"]]


def test_search_products_without_match_returns_empty_list(products_api):
    response = products_api.list(search="inexistente-xyz")

    assert response.status_code == 200
    assert response.json() == []
