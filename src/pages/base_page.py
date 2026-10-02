"""Comportamento comum das Page Objects: esperas explícitas, interações e logging."""
from __future__ import annotations

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils.logger import get_logger

Locator = tuple[str, str]
HTML = (By.TAG_NAME, "html")


class BasePage:
    path = "/"

    def __init__(self, driver: WebDriver, base_url: str, timeout: int = 10) -> None:
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self._wait = WebDriverWait(driver, timeout)
        self.log = get_logger(f"ui.{type(self).__name__}")

    def open(self):
        url = f"{self.base_url}{self.path}"
        self.log.info("Abrindo %s", url)
        self.driver.get(url)
        return self

    def _visible(self, locator: Locator) -> WebElement:
        return self._wait.until(EC.visibility_of_element_located(locator))

    def _type(self, locator: Locator, text: str) -> None:
        element = self._visible(locator)
        element.clear()
        element.send_keys(text)

    def _text(self, locator: Locator) -> str:
        return self._visible(locator).text.strip()

    def _click(self, locator: Locator) -> None:
        self._wait.until(EC.element_to_be_clickable(locator)).click()

    def _click_and_wait_navigation(self, locator: Locator) -> None:
        """Clica e espera o documento atual ser substituído (submit de form / link)."""
        page = self.driver.find_element(*HTML)
        self._click(locator)
        self._wait.until(lambda _: self._is_detached(page))

    @staticmethod
    def _is_detached(element: WebElement) -> bool:
        try:
            element.is_enabled()
        except StaleElementReferenceException:
            return True
        except WebDriverException as exc:
            # Durante a troca de documento o Chrome pode não sinalizar "stale" e sim este erro.
            return "does not belong to the document" in str(exc)
        return False

    def _wait_for_feedback(self, *locators: Locator) -> None:
        """Espera que algum dos elementos de feedback (sucesso/erro) exista na página."""
        self._wait.until(lambda d: any(d.find_elements(*loc) for loc in locators))

    def _is_visible(self, locator: Locator, timeout: float = 3) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located(locator))
            return True
        except TimeoutException:
            return False
