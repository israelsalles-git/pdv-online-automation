from __future__ import annotations

from selenium.webdriver.common.by import By

from src.pages.base_page import BasePage


class CustomersPage(BasePage):
    path = "/customers"

    SEARCH_INPUT = (By.ID, "search-input")
    SEARCH_BUTTON = (By.ID, "search-button")
    NAME = (By.ID, "customer-name")
    DOCUMENT = (By.ID, "customer-document")
    EMAIL = (By.ID, "customer-email")
    SAVE = (By.ID, "save-customer")
    SUCCESS = (By.ID, "message")
    FORM_ERROR = (By.ID, "form-error")
    ROWS = (By.CSS_SELECTOR, "#customers-table tbody tr[data-name]")

    def create_customer(self, name: str, document: str = "", email: str = "") -> None:
        self.log.info("Cadastrando cliente '%s'", name)
        self._type(self.NAME, name)
        self._type(self.DOCUMENT, document)
        self._type(self.EMAIL, email)
        self._click_and_wait_navigation(self.SAVE)
        self._wait_for_feedback(self.SUCCESS, self.FORM_ERROR)

    def search_customer(self, term: str) -> None:
        self.log.info("Pesquisando cliente '%s'", term)
        self._type(self.SEARCH_INPUT, term)
        self._click_and_wait_navigation(self.SEARCH_BUTTON)

    def get_customer_names(self) -> list[str]:
        return [row.get_attribute("data-name") for row in self.driver.find_elements(*self.ROWS)]

    def get_message(self) -> str:
        return self._text(self.SUCCESS)

    def get_form_error(self) -> str:
        return self._text(self.FORM_ERROR)
