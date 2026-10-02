from __future__ import annotations

from selenium.webdriver.common.by import By

from src.pages.base_page import BasePage


class DashboardPage(BasePage):
    path = "/dashboard"

    TITLE = (By.ID, "dashboard-title")
    WELCOME = (By.ID, "welcome-message")
    LOGOUT = (By.ID, "logout")

    def is_loaded(self) -> bool:
        return self._is_visible(self.TITLE)

    def get_welcome_message(self) -> str:
        return self._text(self.WELCOME)

    def logout(self) -> None:
        self.log.info("Logout")
        self._click_and_wait_navigation(self.LOGOUT)
