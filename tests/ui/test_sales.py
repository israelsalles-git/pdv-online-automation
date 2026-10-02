from decimal import Decimal

import pytest

pytestmark = [pytest.mark.ui, pytest.mark.regression]

UNIT_PRICE = Decimal("19.90")  # preço do produto criado pela fixture created_product


@pytest.mark.smoke
def test_complete_sale_flow(sales_page, dashboard_page, created_product):
    assert dashboard_page.is_loaded()
    sales_page.open()

    sales_page.select_product(created_product["code"])
    sales_page.set_quantity(3)
    sales_page.add_to_cart()

    assert sales_page.get_subtotals() == [UNIT_PRICE * 3]
    assert sales_page.get_total() == UNIT_PRICE * 3

    sales_page.finish_sale()

    assert "finalizada com sucesso" in sales_page.get_confirmation_message()
    assert sales_page.get_confirmed_total() == UNIT_PRICE * 3
    assert sales_page.get_cart_size() == 0
    assert sales_page.get_total() == Decimal("0")


@pytest.mark.parametrize("quantity", [1, 2, 7, 25])
def test_subtotal_and_total_follow_quantity(sales_page, created_product, quantity):
    sales_page.open()

    sales_page.add_item(created_product["code"], quantity)

    assert sales_page.get_subtotals() == [UNIT_PRICE * quantity]
    assert sales_page.get_total() == UNIT_PRICE * quantity


def test_total_is_sum_of_different_products(sales_page, created_product):
    sales_page.open()

    sales_page.add_item(created_product["code"], 2)
    sales_page.add_item("1001", 1)  # produto do catálogo de demonstração: Arroz 5kg a R$ 25,90

    assert sales_page.get_cart_size() == 2
    assert sales_page.get_total() == UNIT_PRICE * 2 + Decimal("25.90")


def test_adding_same_product_twice_accumulates_quantity(sales_page, created_product):
    sales_page.open()

    sales_page.add_item(created_product["code"], 1)
    sales_page.add_item(created_product["code"], 2)

    assert sales_page.get_cart_size() == 1
    assert sales_page.get_total() == UNIT_PRICE * 3


def test_finish_sale_with_empty_cart_shows_error(sales_page):
    sales_page.open()

    sales_page.finish_sale()

    assert sales_page.get_error_message() == "Carrinho vazio"


@pytest.mark.parametrize("quantity", ["0", "-1", "abc", "1.5", ""], ids=["zero", "negative", "text", "decimal", "empty"])
def test_invalid_quantity_is_rejected(sales_page, created_product, quantity):
    sales_page.open()

    sales_page.add_item(created_product["code"], quantity)

    assert sales_page.get_error_message() == "Quantidade inválida"
    assert sales_page.get_cart_size() == 0


def test_add_to_cart_without_selecting_product_shows_error(sales_page):
    sales_page.open()

    sales_page.add_to_cart()

    assert sales_page.get_error_message() == "Selecione um produto"
