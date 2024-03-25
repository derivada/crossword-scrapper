import os
from os.path import join, dirname
from dotenv import load_dotenv

# Configuration file
RUN_HEADLESS = False # Run without opening a browser window
# Valid values: "experto", "mambrino", "tarkus"
CROSSWORD_COLLECTION = "experto"

# Secret file paths, add in .env file
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
FIREFOX_PATH = os.environ.get("FIREFOX_PATH") # Path to firefox installation
FIREFOX_PROFILE_PATH = os.environ.get("FIREFOX_PROFILE_PATH") # Path to firefox profile
