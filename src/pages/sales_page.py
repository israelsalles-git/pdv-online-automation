from __future__ import annotations

from decimal import Decimal

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from src.pages.base_page import BasePage
from src.utils.helpers import parse_brl


class SalesPage(BasePage):
    path = "/sales"

    PRODUCT_SELECT = (By.ID, "product-select")
    QUANTITY = (By.ID, "quantity-input")
    ADD_TO_CART = (By.ID, "add-to-cart")
    CART_ROWS = (By.CSS_SELECTOR, "#cart-body tr")
    CART_SUBTOTALS = (By.CSS_SELECTOR, "#cart-body tr .cart-subtotal")
    TOTAL = (By.ID, "cart-total")
    FINISH = (By.ID, "finish-sale")
    ERROR = (By.ID, "sale-error")
    CONFIRMATION = (By.ID, "confirmation-message")
    CONFIRMED_TOTAL = (By.ID, "confirmation-total")

    def select_product(self, code: str) -> None:
        self.log.info("Selecionando produto %s", code)
        Select(self._visible(self.PRODUCT_SELECT)).select_by_value(code)

    def set_quantity(self, quantity: int | str) -> None:
        self._type(self.QUANTITY, str(quantity))

    def add_to_cart(self) -> None:
        self._click(self.ADD_TO_CART)

    def add_item(self, code: str, quantity: int | str = 1) -> None:
        """Atalho: seleciona, informa quantidade e adiciona ao carrinho."""
        self.select_product(code)
        self.set_quantity(quantity)
        self.add_to_cart()

    def get_cart_size(self) -> int:
        return len(self.driver.find_elements(*self.CART_ROWS))

    def get_subtotals(self) -> list[Decimal]:
        return [parse_brl(el.text) for el in self.driver.find_elements(*self.CART_SUBTOTALS)]

    def get_total(self) -> Decimal:
        return parse_brl(self._text(self.TOTAL))

    def finish_sale(self) -> None:
        self.log.info("Finalizando venda")
        self._click(self.FINISH)

    def get_confirmation_message(self) -> str:
        return self._text(self.CONFIRMATION)

    def get_confirmed_total(self) -> Decimal:
        return parse_brl(self._text(self.CONFIRMED_TOTAL))

    def get_error_message(self) -> str:
        return self._text(self.ERROR)
