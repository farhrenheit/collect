import time
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options

TARGET_URL = "https://leon.ru/esports"
SCROLL_PAUSE_TIME = 0.5
DRIVER_PATH = Path(__file__).resolve().parent / "chromedriver"


def get_browser() -> WebDriver:
    options = Options()
    options.add_argument("--headless")
    browser = webdriver.Chrome(str(DRIVER_PATH), options=options)
    return browser


def load_full_page(browser: WebDriver):
    scroll_height = browser.execute_script(
        "return document.querySelector('div[class=content]').scrollHeight"
    )
    scroll_height = scroll_height - 500
    start_scroll_pxl = 0
    window_h = browser.execute_script("return window.innerHeight")
    while start_scroll_pxl < scroll_height - 500:
        browser.execute_script(
            f"document.querySelector('div[class=content]').scroll({start_scroll_pxl}, {start_scroll_pxl + window_h})"
        )
        start_scroll_pxl += window_h
        time.sleep(SCROLL_PAUSE_TIME)
    soup: BeautifulSoup = BeautifulSoup(browser.page_source, "html.parser")
    events = soup.find_all(class_="sport-event-list-item__block")
    return events


def run_parsing():
    # создание и конфигурация браузера
    browser: WebDriver = get_browser()
    # запрос на урл
    browser.get(TARGET_URL)
    # ожидание ответа
    time.sleep(3)

    # скролл страницы, чтобы она прогрузилась полностью
    try:
        events = load_full_page(browser)
        return events
    finally:
        browser.quit()


if __name__ == "__main__":
    run_parsing()
