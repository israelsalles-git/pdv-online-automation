"""Criação do WebDriver conforme BROWSER/HEADLESS."""
from __future__ import annotations

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

from src.utils.logger import get_logger

log = get_logger("driver")
WINDOW_SIZE = "1366,768"


def _chrome(headless: bool) -> WebDriver:
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument(f"--window-size={WINDOW_SIZE}")
    options.add_argument("--no-sandbox")  # necessário em runners Linux de CI
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)


def _firefox(headless: bool) -> WebDriver:
    options = webdriver.FirefoxOptions()
    if headless:
        options.add_argument("-headless")
    driver = webdriver.Firefox(options=options)
    driver.set_window_size(*map(int, WINDOW_SIZE.split(",")))
    return driver


_FACTORIES = {"chrome": _chrome, "firefox": _firefox}


def create_driver(browser: str, headless: bool) -> WebDriver:
    try:
        factory = _FACTORIES[browser]
    except KeyError:
        raise ValueError(f"BROWSER '{browser}' não suportado. Use: {', '.join(_FACTORIES)}") from None
    log.info("Iniciando %s (headless=%s)", browser, headless)
    return factory(headless)
