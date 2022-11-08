#!/usr/bin/env python
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
from datetime import datetime, timedelta


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
        for container in containers:
            if not container:
                continue
            try:
                if not container.div.div:
                    empty_g=empty_g+1
                else:
                    fully_g=fully_g+1
                if remove_heads:
                    head_containers = container.find_all(class_="sport-event-list-sport-headline")
                    for head in head_containers:
                        head.clear()
                # check international
                if EVENT_TITLE in str(container):
                    dota_events.append(container)
            except AttributeError:
                empty_g=empty_g+1
        print(f'|  empty:', empty_g)
        print(f'|  fully:', fully_g)
        print(f'|   events found:', len(dota_events))
        return dota_events

    @staticmethod
    def get_data_from_dota_events(dota_events):
        ev_num = 0
        
        for container in dota_events:
            dota_games = container.find_all(class_="sport-event-list-item__block")
            add_g = add_c = 0
            ev_num=ev_num+1
            for game in dota_games:
                # get team names
                titles = game.find_all(
                    "span", attrs={"class": "sport-event-list-item-competitor__name"}
                )
                t_one_name, t_two_name = [i.text.strip() for i in titles]
                with get_db() as session:
                    # проверяем, есть ли запись игры в БД
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
                    # если игры нет - записываем ее
                    elif not game_schema:
                        new_game = GameSchema(
                            id=uuid4(), team_one=t_one_name, team_two=t_two_name
                        )
                        session.add(new_game)
                        session.commit()
                        add_g=add_g+1
                        g_id = new_game.id
                        print(f'|    *new game:', t_one_name, 'x', t_two_name)
                    ##print([i.text.strip() for i in titles])
                    # get koef
                    coefs = game.find_all(
                        "span",
                        attrs={"class": "sport-event-list-item-market__coefficient"},
                    )
                    coef_info = [i.text.strip() for i in coefs]
                    ##print(coef_info)
                    t_plus = '0'
                    for c in coef_info:
                        if '+' in c:
                            t_plus = c
                    coef_info.remove(c)
                    if len(coef_info) == 0: # [+20] 
                        t_one_coef = t_two_coef = t_draw = coef_info = '0'
                    if len(coef_info) == 2: # [1.5,2.5]
                        t_one_coef, t_two_coef = coef_info
                        t_draw = '0'
                    elif len(coef_info) == 3: #[1.5,2.5,1.8]
                        t_one_coef, t_two_coef, t_draw = coef_info
                    
                    # Проверяем есть ли запись коэффициента в db
                    
                    coef_schema: CoeffSchema = (
                        (
                            session.execute(
                                select(CoeffSchema).where(
                                    CoeffSchema.game_id == g_id,
                                    CoeffSchema.w_one == t_one_coef,
                                    CoeffSchema.draw == t_draw,
                                    CoeffSchema.w_two == t_two_coef,
                                    CoeffSchema.plus == t_plus,
                                )
                            )
                        )
                        .scalars().all()
                    )
                    if coef_schema:
                        _timestamp = coef_schema[-1].timestamp
                        if datetime.now() - _timestamp < timedelta(minutes=1):
                            continue
                    coef_schema = CoeffSchema(
                        game_id=g_id,
                        w_one=t_one_coef,
                        draw=t_draw,
                        w_two=t_two_coef,
                        plus=t_plus,
                        timestamp=datetime.now(),
                        id=uuid4()
                    )
                    session.add(coef_schema)
                    session.commit()
                    add_c=add_c+1
                    ##------------------------
                        
            if add_g != 0: print(f'|---> ev[',ev_num,']:> new games writed:', add_g)
            if add_c != 0: print(f'|----> ev[',ev_num,']:> new coeffs writed:', add_c)

    def run(self):
        uptime = datetime.now()
        # запрос на урл
        self.browser.get(self.TARGET_URL)
        # ожидание ответа
        time.sleep(RESPONE_INIT_PAUSE)
        # скролл страницы, чтобы она прогрузилась полностью
        try:
            self._load_full_page()
            for cnt in range(1,15):
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

