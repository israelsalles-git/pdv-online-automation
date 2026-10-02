import pytest

from src.models import Customer

pytestmark = [pytest.mark.ui, pytest.mark.regression]


def test_create_customer(customers_page):
    customer = Customer.build()
    customers_page.open()

    customers_page.create_customer(customer.name, customer.document, customer.email)

    assert customers_page.get_message() == "Cliente cadastrado com sucesso"
    assert customer.name in customers_page.get_customer_names()


@pytest.mark.parametrize(
    "name, email, expected_error",
    [("", "a@example.com", "Nome é obrigatório"), ("Cliente", "sem-arroba", "E-mail inválido")],
    ids=["no_name", "invalid_email"],
)
def test_create_customer_with_invalid_data(customers_page, name, email, expected_error):
    customers_page.open()

    customers_page.create_customer(name, email=email)

    assert customers_page.get_form_error() == expected_error


def test_search_customer(customers_page, created_customer):
    customers_page.open()

    customers_page.search_customer(created_customer["name"])

    assert customers_page.get_customer_names() == [created_customer["name"]]
