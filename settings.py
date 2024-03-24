import os
from os.path import join, dirname
from dotenv import load_dotenv

# Run without opening a browser window
RUN_HEADLESS = False

# Secret paths
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
FIREFOX_PATH = os.environ.get("FIREFOX_PATH")
GECKODRIVER_PATH = os.environ.get("GECKODRIVER_PATH")
FIREFOX_PROFILE_PATH = os.environ.get("FIREFOX_PROFILE_PATH")
