from __future__ import annotations

from selenium.webdriver.common.by import By

from src.pages.base_page import BasePage


class LoginPage(BasePage):
    path = "/login"

    USERNAME = (By.ID, "username")
    PASSWORD = (By.ID, "password")
    LOGIN_BUTTON = (By.ID, "login-button")
    ERROR = (By.ID, "login-error")

    def enter_username(self, username: str) -> None:
        self._type(self.USERNAME, username)

    def enter_password(self, password: str) -> None:
        self._type(self.PASSWORD, password)

    def click_login(self) -> None:
        self._click_and_wait_navigation(self.LOGIN_BUTTON)

    def login(self, username: str, password: str) -> None:
        self.log.info("Login com usuário '%s'", username)
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()

    def get_error_message(self) -> str:
        return self._text(self.ERROR)

    def is_loaded(self) -> bool:
        return self._is_visible(self.LOGIN_BUTTON)
