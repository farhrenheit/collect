from pathlib import Path

SCROLL_PAUSE_TIME = 1
RESPONE_INIT_PAUSE = 5
DRIVER_PATH = Path(__file__).resolve().parent / "chromedriver"
EVENT_TITLE = "Dota"
DATABSE_URL = "postgresql+pg8000://user:@localhost:5432/template2"
IS_LIN_OS = False
DROP = True