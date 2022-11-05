import time
import os
from uuid import uuid4
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from settings import SCROLL_PAUSE_TIME, DRIVER_PATH, RESPONE_INIT_PAUSE, EVENT_TITLE
from db import Base, get_db
from sqlalchemy import select
from models import GameSchema, CoeffSchema
from datetime import datetime


class LeonParser:
    TARGET_URL = "https://leon.ru/esports/"

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
        def check_h():
            return self.browser.execute_script(
                "return document.querySelector('div[class=content]').scrollHeight"
            )
        def scroll(start_h, end_h):
                self.browser.execute_script(
                f"document.querySelector('div[class=content]').scroll({start_h}, {end_h})"
            )
        window_h = self.browser.execute_script("return window.innerHeight")
        temp_h = window_h
        start_scroll_h = 0
        print("\nscrolling-", end='')
        while check_h() > temp_h:
            scroll(start_scroll_h, temp_h)
            start_scroll_h += window_h
            temp_h += window_h
            print('>', end='', flush=True)
            time.sleep(SCROLL_PAUSE_TIME)
        scroll(temp_h,200) ## scroll up
        print("|done")
        
    def find_dota_events(self, remove_heads=True):
        empty_g = 0
        fully_g = 0
        soup: BeautifulSoup = BeautifulSoup(self.browser.page_source, "html.parser")
        containers = soup.find_all(class_="group--shown")
        print(f"| containers found:", len(containers))
        dota_events = []
        for event in containers:
            if not event:
                continue
            try:
                if remove_heads:
                    head_containers = event.find_all(class_="sport-event-list-sport-headline")
                    for head in head_containers:
                        head.clear()
                # check international
                if EVENT_TITLE in str(event):
                    dota_events.append(event)
                fully_g=+1
            except AttributeError:
                empty_g=empty_g+1
        print(f'|  empty:', empty_g)
        print(f'|  fully:', fully_g)
        print(f'|   events found:', len(dota_events))
        return dota_events

    @staticmethod
    def get_data_from_dota_events(dota_events):
        ev_num=0
        for container in dota_events:
            dota_games = container.find_all(class_="sport-event-list-item__block")
            ev_num=ev_num+1
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
                    if game_schema:
                        g_id = game_schema.id
                    elif not game_schema:
                        new_game = GameSchema(
                            id=uuid4(), team_one=t_one_name, team_two=t_two_name
                        )
                        session.add(new_game)
                        session.commit()
                        g_id = new_game.id
                        print(f'|--- *new game:', t_one_name, 'x', t_two_name)
                    ##print([i.text.strip() for i in titles])
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
                        
            print(f'|-> ev[',ev_num,']:> games uploaded to db:', len(dota_games))

    def run(self):
        uptime = datetime.now()
        # запрос на урл
        self.browser.get(self.TARGET_URL)
        # ожидание ответа
        time.sleep(RESPONE_INIT_PAUSE)
        # скролл страницы, чтобы она прогрузилась полностью
        try:
            self._load_full_page()
            for cnt in range(1,4):
                start_time = time.time()
                print(f'\nIteration ', cnt,' started at ', datetime.now())
                dota_events = self.find_dota_events()
                self.get_data_from_dota_events(dota_events)
                job_time = time.time() - start_time
                print(f'Iteration ', cnt,' finished  |  job time: ', job_time, ' |  uptime: ', datetime.now()-uptime, flush=True)  
                time.sleep(1+cnt%2)      
        finally:
            self.browser.quit()
            

if __name__ == "__main__":
    Base.metadata.drop_all()
    Base.metadata.create_all()
    parser = LeonParser()
    parser.run()

