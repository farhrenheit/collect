import time
import logging
from uuid import uuid4
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from settings import SCROLL_PAUSE_TIME, DRIVER_PATH, RESPONE_INIT_PAUSE, EVENT_TITLE, OS, DROP
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
        if OS == 'LIN':
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            browser = webdriver.Chrome(executable_path=DRIVER_PATH, options=options)
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
                game_id = parser.check_write('s_game', [t_one_name, t_two_name])
                # get koef
                coefs = game.find_all(
                    "span",
                    attrs={"class": "sport-event-list-item-market__coefficient"},
                )
                coef_info = [i.text.strip() for i in coefs]
                coef_info.append(game_id)
                parser.check_write('coef_by_game', coef_info)
    
    def check_write(self, schema, data):
        with get_db() as session:
               
            if schema == 's_game':
                # проверяем, есть ли запись игры в БД
                game_schema: GameSchema = (
                    (
                        session.execute(
                            select(GameSchema).where(
                                GameSchema.team_one == data[0],
                                        GameSchema.team_two == data[1],
                            )
                        )
                    ) # добавить разделение по сериям 
                    .scalars()
                    .one_or_none()
                )
                if game_schema:
                    return game_schema.id
                # если игры нет - записываем ее
                new_game = GameSchema(
                    id=uuid4(), team_one=data[0], team_two=data[1]
                )
                session.add(new_game)
                session.commit()
                print(f'|    *new game:', data[0], 'x', data[1])
                return new_game.id

            if schema == 'coef_by_game':
                # придаём коэффициенту структуру для записи в БД
                if len(data) == 2: # [+20, game_id] 
                    struct_data = [data[1],None,None,None,''.join(filter(str.isdigit,data[0]))]
                if len(data) == 3: # [1.5,2.5, game_id]
                    struct_data = [data[2],data[0],None,data[1],None]
                elif len(data) == 4: #[1.5,2.5,1.8, game_id]
                    struct_data = [data[3],data[0],None,data[1],data[2]]
                elif len(data) == 5: #[1.5,2.5,1.8, +20 game_id]
                    struct_data = [data[4],data[0],data[1],data[2],''.join(filter(str.isdigit,data[3]))]
                # Проверяем есть ли запись коэффициента в db
                coef_schema: CoeffSchema = (
                    (
                        session.execute(
                            select(CoeffSchema).where(
                                CoeffSchema.game_id == struct_data[0],
                                CoeffSchema.w_one == struct_data[1],
                                CoeffSchema.draw == struct_data[2],
                                CoeffSchema.w_two == struct_data[3],
                                CoeffSchema.plus == struct_data[4],
                            )
                        )
                    )
                    .scalars().all()
                )
                if coef_schema:
                    _timestamp = coef_schema[-1].timestamp
                    if datetime.now() - _timestamp < timedelta(minutes=1):
                        return print('coef exist')
                coef_schema = CoeffSchema(
                    game_id=struct_data[0],
                    w_one=struct_data[1],
                    draw=struct_data[2],
                    w_two=struct_data[3],
                    plus=struct_data[4],
                    timestamp=datetime.now(),
                    id=uuid4()
                )
                session.add(coef_schema)
                session.commit()
                return coef_schema.id
                
            
            
    def run(self):
        uptime = datetime.now()
        # запрос на урл
        self.browser.get(self.TARGET_URL)
        # ожидание ответа
        time.sleep(RESPONE_INIT_PAUSE)
        # скролл страницы, чтобы она прогрузилась полностью
        try:
            self._load_full_page()
            # запуск парсера
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
    if DROP:
        Base.metadata.drop_all()
    Base.metadata.create_all()
    parser = LeonParser()
    parser.run()

