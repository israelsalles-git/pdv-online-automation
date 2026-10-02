from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from selenium.webdriver.common.by import By

from src.pages.base_page import BasePage, Locator
from src.utils.helpers import parse_brl


@dataclass(frozen=True)
class ProductRow:
    code: str
    name: str
    price: Decimal
    ncm: str


class ProductsPage(BasePage):
    path = "/products"

    SEARCH_INPUT = (By.ID, "search-input")
    SEARCH_BUTTON = (By.ID, "search-button")
    CODE = (By.ID, "product-code")
    NAME = (By.ID, "product-name")
    PRICE = (By.ID, "product-price")
    NCM = (By.ID, "product-ncm")
    SAVE = (By.ID, "save-product")
    SUCCESS = (By.ID, "message")
    FORM_ERROR = (By.ID, "form-error")
    ROWS = (By.CSS_SELECTOR, "#products-table tbody tr[data-code]")

    @staticmethod
    def _row_css(code: str) -> str:
        return f"#products-table tr[data-code='{code}']"

    def _row_button(self, code: str, button_class: str) -> Locator:
        return By.CSS_SELECTOR, f"{self._row_css(code)} .{button_class}"

    def _save_and_wait_feedback(self) -> None:
        self._click_and_wait_navigation(self.SAVE)
        self._wait_for_feedback(self.SUCCESS, self.FORM_ERROR)

    def create_product(self, code: str, name: str, price: str | float | Decimal, ncm: str = "") -> None:
        self.log.info("Cadastrando produto %s - %s", code, name)
        self._type(self.CODE, code)
        self._type(self.NAME, name)
        self._type(self.PRICE, str(price))
        self._type(self.NCM, ncm)
        self._save_and_wait_feedback()

    def search_product(self, term: str) -> None:
        self.log.info("Pesquisando produto '%s'", term)
        self._type(self.SEARCH_INPUT, term)
        self._click_and_wait_navigation(self.SEARCH_BUTTON)

    def edit_product(self, code: str, name: str | None = None, price: str | float | Decimal | None = None) -> None:
        self.log.info("Editando produto %s", code)
        self._click_and_wait_navigation(self._row_button(code, "edit-button"))
        if name is not None:
            self._type(self.NAME, name)
        if price is not None:
            self._type(self.PRICE, str(price))
        self._save_and_wait_feedback()

    def delete_product(self, code: str) -> None:
        self.log.info("Excluindo produto %s", code)
        self._click_and_wait_navigation(self._row_button(code, "delete-button"))
        self._wait_for_feedback(self.SUCCESS, self.FORM_ERROR)

    def get_message(self) -> str:
        return self._text(self.SUCCESS)

    def get_form_error(self) -> str:
        return self._text(self.FORM_ERROR)

    def get_product(self, code: str) -> ProductRow | None:
        rows = self.driver.find_elements(By.CSS_SELECTOR, self._row_css(code))
        if not rows:
            return None

        def cell(css: str) -> str:
            return rows[0].find_element(By.CSS_SELECTOR, css).text.strip()

        return ProductRow(cell(".code"), cell(".name"), parse_brl(cell(".price")), cell(".ncm"))

    def get_listed_codes(self) -> list[str]:
        return [row.get_attribute("data-code") for row in self.driver.find_elements(*self.ROWS)]
