import pytest

from src.api import schemas
from src.models import SaleItem
from src.utils.helpers import as_params, assert_schema, load_test_data, money

pytestmark = [pytest.mark.api, pytest.mark.regression]

INVALID_QUANTITIES = load_test_data("products.json")["invalid_quantities"]


def _payload(*items: SaleItem, **extra) -> dict:
    return {"items": [item.to_payload() for item in items], **extra}


@pytest.mark.smoke
def test_create_sale_with_existing_product(sales_api, created_product):
    response = sales_api.create(_payload(SaleItem(created_product["id"], 2)))

    assert response.status_code == 201
    sale = response.json()
    assert_schema(sale, schemas.SALE)
    assert sale["status"] == "completed"
    assert sale["items"][0]["product_id"] == created_product["id"]
    assert sale["items"][0]["unit_price"] == created_product["price"]
    assert sale["total"] == pytest.approx(created_product["price"] * 2)


@pytest.mark.parametrize("quantity", [1, 3, 10, 100])
def test_sale_total_is_unit_price_times_quantity(sales_api, created_product, quantity):
    sale = sales_api.create(_payload(SaleItem(created_product["id"], quantity))).json()

    expected = money(created_product["price"]) * quantity
    assert money(sale["items"][0]["subtotal"]) == expected
    assert money(sale["total"]) == expected


def test_sale_total_is_sum_of_item_subtotals(sales_api, products_api, created_product):
    other = products_api.get(1).json()  # produto do catálogo de demonstração

    sale = sales_api.create(_payload(SaleItem(created_product["id"], 2), SaleItem(other["id"], 3))).json()

    assert len(sale["items"]) == 2
    assert sum(money(i["subtotal"]) for i in sale["items"]) == money(sale["total"])
    assert money(sale["total"]) == money(created_product["price"]) * 2 + money(other["price"]) * 3


def test_created_sale_can_be_retrieved(sales_api, created_product):
    sale_id = sales_api.create(_payload(SaleItem(created_product["id"], 1))).json()["id"]

    response = sales_api.get(sale_id)

    assert response.status_code == 200
    assert response.json()["id"] == sale_id


def test_sale_with_existing_customer(sales_api, created_product, created_customer):
    response = sales_api.create(_payload(SaleItem(created_product["id"], 1), customer_id=created_customer["id"]))

    assert response.status_code == 201
    assert response.json()["customer_id"] == created_customer["id"]


def test_sale_with_unknown_customer_returns_404(sales_api, created_product):
    response = sales_api.create(_payload(SaleItem(created_product["id"], 1), customer_id=999_999))

    assert response.status_code == 404
    assert response.json()["error"] == "Cliente não encontrado"


def test_sale_with_unknown_product_returns_404(sales_api):
    response = sales_api.create(_payload(SaleItem(999_999, 1)))

    assert response.status_code == 404
    assert_schema(response.json(), schemas.ERROR)
    assert "999999" in response.json()["error"]


@pytest.mark.parametrize("case", as_params(INVALID_QUANTITIES))
def test_sale_with_invalid_quantity(sales_api, created_product, case):
    response = sales_api.create({"items": [{"product_id": created_product["id"], "quantity": case["value"]}]})

    assert response.status_code == 400
    assert response.json()["error"] == "Quantidade inválida"


@pytest.mark.parametrize("payload", [{"items": []}, {}, {"items": None}], ids=["empty_list", "missing", "null"])
def test_sale_with_empty_cart(sales_api, payload):
    response = sales_api.create(payload)

    assert response.status_code == 400
    assert response.json()["error"] == "Carrinho vazio"


def test_get_unknown_sale_returns_404(sales_api):
    assert sales_api.get(999_999).status_code == 404


def test_sale_requires_authentication(anonymous_client):
    response = anonymous_client.post("/sales", json={"items": []})

    assert response.status_code == 401
