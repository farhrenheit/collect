import time
from uuid import uuid4
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from settings import SCROLL_PAUSE_TIME, DRIVER_PATH
from db import Base, get_db
from sqlalchemy import select
from models import GameSchema, CoeffSchema
from datetime import datetime


class LeonParser:
    TARGET_URL = "https://leon.ru/esports"

    def __init__(
        self,
    ):
        self.browser = self._browser

    @property
    def _browser(self):
        options = Options()
        # options.add_argument("--headless")
        browser = webdriver.Chrome(str(DRIVER_PATH), options=options)
        return browser

    def _load_full_page(self):
        scroll_height = self.browser.execute_script(
            "return document.querySelector('div[class=content]').scrollHeight"
        )
        scroll_height = scroll_height - 500
        start_scroll_pxl = 0
        window_h = self.browser.execute_script("return window.innerHeight")
        while start_scroll_pxl < scroll_height - 500:
            print("scrolling")
            self.browser.execute_script(
                f"document.querySelector('div[class=content]').scroll({start_scroll_pxl}, {start_scroll_pxl + window_h})"
            )
            start_scroll_pxl += window_h
            time.sleep(SCROLL_PAUSE_TIME)

    def find_dota_events(self):
        soup: BeautifulSoup = BeautifulSoup(self.browser.page_source, "html.parser")
        events = soup.find_all(class_="group--shown")
        print(len(events))
        dota_events = []
        for event in events:
            if not event:
                continue
            try:
                lbl = event.div.div.div.div.span.text
                # check international
                if lbl == "CS:GO":
                    dota_events.append(event)
            except AttributeError:
                print("empty group")
        return dota_events

    @staticmethod
    def get_data_from_dota_events(dota_events):
        for event in dota_events:
            dota_games = event.find_all(class_="sport-event-list-item__block")

            for game in dota_games:
                # get team names
                titles = game.find_all(
                    "span", attrs={"class": "sport-event-list-item-competitor__name"}
                )
                t_one_name, t_two_name = [i.text.strip() for i in titles]
                with get_db() as session:

                    game_schema: GameSchema = (
                        (
                            session.execute(
                                select(GameSchema).where(
                                    GameSchema.team_one == t_one_name,
                                    GameSchema.team_two == t_two_name,
                                )
                            )
                        )
                        .scalars()
                        .one_or_none()
                    )
                    g_id = game_schema.id
                    if not game_schema:
                        new_game = GameSchema(
                            id=uuid4(), team_one=t_one_name, team_two=t_two_name
                        )
                        session.add(new_game)
                        session.commit()
                        g_id = new_game.id
                    print([i.text.strip() for i in titles])
                    # get koef
                    coefs = game.find_all(
                        "span",
                        attrs={"class": "sport-event-list-item-market__coefficient"},
                    )
                    coef_info = [i.text.strip() for i in coefs]

                    if len(coef_info) == 3:
                        t_one_coef, t_two_coef, _ = coef_info
                        coef_schema = CoeffSchema(
                            id=uuid4(),
                            game_id=g_id,
                            w_one=t_one_coef,
                            t="0",
                            w_two=t_two_coef,
                            timestamp=datetime.now(),
                        )
                        session.add(coef_schema)
                        session.commit()

                    print(coef_info)

            print(len(dota_games))

    def run(self):
        # запрос на урл
        self.browser.get(self.TARGET_URL)
        # ожидание ответа
        time.sleep(5)
        # скролл страницы, чтобы она прогрузилась полностью
        try:
            self._load_full_page()
            dota_events = self.find_dota_events()
            self.get_data_from_dota_events(dota_events)
        finally:
            self.browser.quit()


if __name__ == "__main__":
    Base.metadata.drop_all()
    Base.metadata.create_all()
    parser = LeonParser()
    parser.run()
