from decimal import Decimal

import pytest

from src.models import Product

pytestmark = [pytest.mark.ui, pytest.mark.regression]


@pytest.mark.smoke
def test_create_product(products_page):
    product = Product.build(name="Biscoito Recheado 130g", price="3.49", ncm="19053100")
    products_page.open()

    products_page.create_product(product.code, product.name, product.price, product.ncm)

    assert products_page.get_message() == "Produto cadastrado com sucesso"
    row = products_page.get_product(product.code)
    assert row is not None
    assert (row.name, row.price, row.ncm) == ("Biscoito Recheado 130g", Decimal("3.49"), "19053100")


@pytest.mark.parametrize(
    "name, price, expected_error",
    [
        ("", "10.00", "Nome é obrigatório"),
        ("Produto sem preço", "", "Preço inválido"),
        ("Produto preço zero", "0", "Preço inválido"),
        ("Produto preço negativo", "-3,50", "Preço inválido"),
        ("Produto preço texto", "abc", "Preço inválido"),
    ],
    ids=["no_name", "no_price", "zero_price", "negative_price", "text_price"],
)
def test_create_product_with_invalid_data(products_page, name, price, expected_error):
    product = Product.build()
    products_page.open()

    products_page.create_product(product.code, name, price)

    assert products_page.get_form_error() == expected_error
    products_page.open()
    assert products_page.get_product(product.code) is None


def test_create_product_accepts_comma_as_decimal_separator(products_page):
    product = Product.build()
    products_page.open()

    products_page.create_product(product.code, product.name, "12,34")

    assert products_page.get_product(product.code).price == Decimal("12.34")


def test_create_product_with_duplicate_code(products_page, created_product):
    products_page.open()

    products_page.create_product(created_product["code"], "Outro nome", "5.00")

    assert products_page.get_form_error() == "Código já cadastrado"


@pytest.mark.smoke
def test_search_product_by_name(products_page, created_product):
    products_page.open()

    products_page.search_product(created_product["name"])

    assert created_product["code"] in products_page.get_listed_codes()


def test_search_product_by_code_filters_the_list(products_page, created_product):
    products_page.open()

    products_page.search_product(created_product["code"])

    assert products_page.get_listed_codes() == [created_product["code"]]


def test_search_product_without_match_shows_empty_list(products_page):
    products_page.open()

    products_page.search_product("inexistente-xyz")

    assert products_page.get_listed_codes() == []


def test_edit_product(products_page, created_product):
    products_page.open()

    products_page.edit_product(created_product["code"], name="Produto Editado", price="33.30")

    assert products_page.get_message() == "Produto atualizado com sucesso"
    row = products_page.get_product(created_product["code"])
    assert (row.name, row.price) == ("Produto Editado", Decimal("33.30"))


def test_edit_product_with_invalid_price_keeps_original_data(products_page, created_product):
    products_page.open()

    products_page.edit_product(created_product["code"], price="-1")

    assert products_page.get_form_error() == "Preço inválido"
    products_page.open()
    assert products_page.get_product(created_product["code"]).price == Decimal("19.90")


def test_delete_product(products_page, created_product):
    products_page.open()

    products_page.delete_product(created_product["code"])

    assert products_page.get_message() == "Produto excluído com sucesso"
    assert products_page.get_product(created_product["code"]) is None
