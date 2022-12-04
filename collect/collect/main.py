import time
import logging
import os
from uuid import uuid4
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from settings import SCROLL_PAUSE_TIME, DRIVER_PATH, RESPONE_INIT_PAUSE, EVENT_TITLE, IS_LIN_OS, DROP
from db import Base, get_db
from sqlalchemy import select
from models import GameSchema, CoeffSchema
from datetime import datetime, timedelta


class LeonParser:
    TARGET_URL = "https://leon.ru/esports/dota-2"

    def __init__(
        self,
    ):
        self.browser = self._browser

    @property
    def _browser(self):
        options = Options()
        if IS_LIN_OS:
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            #browser = webdriver.Chrome(executable_path=DRIVER_PATH, options=options)
        browser = webdriver.Chrome(str(DRIVER_PATH), options=options)
        logging.info('Browser was init with IS_LIN_OS: %s', IS_LIN_OS)
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
        soup: BeautifulSoup = BeautifulSoup(self.browser.page_source, "html.parser")
        main_container = soup.find(class_="group--shown")
        league = main_container.find_all(class_="league-element-inner__holder") 
        liveg = 0
        dota_events = []
        for container in league: 
            dota_events.append(container)
            if not container:
                continue
            try:
                if not "Через" in container.parent.text:
                    liveg = liveg + 1
            except AttributeError:  
                logging.exception('find_dota_events AttributeError')
        print(f'|  Live events found:', liveg)
        print(f'|  Overall events found:', len(dota_events))
        return dota_events

    @staticmethod
    def get_data_from_dota_events(dota_events):  
        coeff_upd = gcount = glcount = 0
        for container in dota_events:
            dota_games = container.find_all(class_="sport-event-list-item__block")
            for game in dota_games:
                # get team names
                titles = game.find_all(
                    "span", attrs={"class": "sport-event-list-item-competitor__name"}
                )
                if game.find(class_="live-progress__stage"):
                    glcount = glcount + 1
                gcount = gcount + 1
                t_one_name, t_two_name = [i.text.strip() for i in titles]
                game_id = parser.check_write('s_game', [t_one_name, t_two_name])
                # get koef
                coefs = game.find_all(
                    "span",
                    attrs={"class": "sport-event-list-item-market__coefficient"},
                )
                coef_info = [i.text.strip() for i in coefs]
                coef_info.append(game_id)
                if parser.check_write('coef_by_game', coef_info): coeff_upd += 1
        # logging finished iteration
        print(f'|   - live games found:', glcount)
        print(f'|   - overall games found:', gcount)
        if coeff_upd != 0:
            print(f'|   *', coeff_upd,' game coeffs was updated')
        #return len(coef_info)
        
    
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
                    logging.info('Existed game %s x %s found.', data[0], data[1])
                    return game_schema.id
                # если игры нет - записываем ее
                new_game = GameSchema(
                    id=uuid4(), team_one=data[0], team_two=data[1], game_found=datetime.now()
                )
                session.add(new_game)
                session.commit()
                print(f'|    *new game:', data[0], 'x', data[1])
                return new_game.id

            if schema == 'coef_by_game':
                # придаём коэффициенту структуру для записи в БД
                if len(data) == 1:   # [game_id]
                    struct_data = [data[0],None,None,None,None,False]
                elif len(data) == 2: # [+20, game_id]
                    struct_data = [data[1],None,None,None,''.join(filter(str.isdigit,data[0])),False]
                elif len(data) == 3: # [1.5,2.5, game_id]
                    struct_data = [data[2],data[0],None,data[1],None,False]
                elif len(data) == 4: #[1.5,2.5,1.8, game_id]
                    struct_data = [data[3],data[0],None,data[1],data[2],False]
                elif len(data) == 5: #[1.5,2.5,1.8, +20 game_id]
                    struct_data = [data[4],data[0],data[1],data[2],''.join(filter(str.isdigit,data[3])),False]
                else: return logging.critical('Unexpected lenght of data: %s |data: %s', len(data), data)
                # Проверяем есть ли запись коэффициента в db
                try:
                    coef_schema: CoeffSchema = (
                        (
                            session.execute(
                                select(CoeffSchema).where(
                                    CoeffSchema.game_id == struct_data[0],
                                    CoeffSchema.w_one == struct_data[1],
                                    CoeffSchema.draw == struct_data[2],
                                    CoeffSchema.w_two == struct_data[3],
                                    CoeffSchema.plus == struct_data[4],
                                )   # stucture: [game_id, w_one, draw, w_two, plus, dupl]
                            )
                        )
                        .scalars().all()
                    )
                    if coef_schema:
                        struct_data[5] = True
                        _timestamp = coef_schema[-1].timestamp
                        if datetime.now() - _timestamp < timedelta(minutes=1):
                            logging.debug('Existed coef %s found.', struct_data[0])
                            return False
                    coef_schema = CoeffSchema(
                        game_id=struct_data[0],
                        w_one=struct_data[1],
                        draw=struct_data[2],
                        w_two=struct_data[3],
                        plus=struct_data[4],
                        dupl=struct_data[5],
                        timestamp=datetime.now(),
                        id=uuid4()
                    )
                    session.add(coef_schema)
                    session.commit()
                    return True
                except UnboundLocalError:
                    return logging.critical('Problem with coef_schema checking | %s', coef_schema)
            
            
    def run(self):
        uptime = datetime.now()
        # запрос на урл
        self.browser.get(self.TARGET_URL)
        # ожидание ответа
        time.sleep(RESPONE_INIT_PAUSE)
        # скролл страницы, чтобы она прогрузилась полностью
        try:
            self._load_full_page()
            for cnt in range(1,10000000):
                start_time = time.time()
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f'\nIteration ', cnt,' started at ', datetime.now(), flush=True)
                dota_events = self.find_dota_events()
                self.get_data_from_dota_events(dota_events)
                job_time = time.time() - start_time
                print('Iteration ', cnt,' finished  |  job time: ', job_time, ' |  uptime: ', datetime.now()-uptime, flush=True)
                logging.info('Iteration %s finished  |  job time:  %s |  uptime:  %s ', cnt, job_time, datetime.now()-uptime)
                time.sleep(1+cnt%2*0.4)  
        except KeyboardInterrupt:
                logging.critical('Python app was closed by Keyboard Interrupt')
                logging.disable(logging.CRITICAL)
        finally:
            logging.critical('Parser loop is finished.')
            self.browser.quit()


if __name__ == "__main__":
    logging.basicConfig(filename='worker.log', encoding='utf-8', level=logging.INFO)
    if DROP:
        print('Please approve dropping of database (write "drop"), or press Enter to continue without cleaning.')
        if input() == 'drop':
            Base.metadata.drop_all()
            logging.warning('db was dropped due app starting')
    Base.metadata.create_all()
    parser = LeonParser()
    try:
        if parser.browser:
            logging.info('Parser object was created, running...') 
            parser.run()
    except Exception as e: 
            logging.critical(f'parses object creating/runnung error:', e) 
  

