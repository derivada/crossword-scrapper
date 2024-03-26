import os
from os.path import join, dirname
from dotenv import load_dotenv

# Configuration file
RUN_HEADLESS = False # Run without opening a browser window

# Valid values: "experto", "mambrino", "tarkus", "mini"
CROSSWORD_COLLECTION = "mini"
START_DATE = "20210701" # Lowest date with crosswords in all 3 categories: 2021/07/01, a column mambrino edge case is at 2021/07/21
END_DATE = "20240326"
DATA_FILE = "data_mini.pkl"
ANALYSIS_COLLECTIONS = ["tarkus", "mambrino", "experto"]
ANALYSIS_DATA_FILES = ["data_tarkus.pkl", "data_mambrino.pkl", "data_experto.pkl"]
SKIP = [("experto", "20230103"), ("tarkus", "20211225"), ("tarkus", "20220609"), ("tarkus", "20220524"),  ("experto", "20231207"), ("experto", "20231226"),
        ("experto", "20231227"),("experto", "20231228"),("experto", "20231229")] # Special crosswords that crash the scraper and are not worth the added complexity of scraping them

# Secret file paths, add in .env file
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
FIREFOX_PATH = os.environ.get("FIREFOX_PATH") # Path to firefox installation
FIREFOX_PROFILE_PATH = os.environ.get("FIREFOX_PROFILE_PATH") # Path to firefox profile