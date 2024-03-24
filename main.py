from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from settings import FIREFOX_PATH, FIREFOX_PROFILE_PATH, RUN_HEADLESS
import pandas as pd
from tqdm import tqdm
from utils import *

def scrape_crossword(crossword_html):
    # We scrape the data using beautiful soup
    soup = BeautifulSoup(crossword_html, "lxml")

def main():
    driver = None
    start_date = "20230102"
    end_date = "20240101"
    date_list = date_range(start_date, end_date)
    try:
        # Setup the browser
        options = webdriver.FirefoxOptions()
        if(RUN_HEADLESS):
            options.add_argument('--headless')
        profile = webdriver.FirefoxProfile(FIREFOX_PROFILE_PATH)
        driver = webdriver.Firefox(firefox_binary=FIREFOX_PATH, executable_path="geckodriver.exe", options=options, firefox_profile=profile)
        acceptedCookies = False
        pbar = tqdm(date_list)
        for date in pbar:
            # Open page
            driver.get(f'https://elpais.com/juegos/crucigramas/mambrino/?id=elpais-mambrino_{date}_0300')

            # Cookie consent needs to be given in first iteration
            if not acceptedCookies:
                pbar.update(1) # Add dummy it. for getting more precise avg. time
                try:
                    cookie_consent_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.pmConsentWall-button')))
                    cookie_consent_button.click()
                    acceptedCookies = True
                except TimeoutException:
                    pass  # Continue even if no cookie consent popup is found

            # Wait for crossword iframe to load and switch to it
            crossword_iframe = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.gm_i-c iframe')))
            driver.switch_to.frame(crossword_iframe)

            # Get the parent crossword element
            crossword = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.puzzle-type-crossword')))
            crossword_html = crossword.get_attribute('outerHTML')
            scrape_crossword(crossword_html)
            pbar.set_description(f"Current data: {convert_to_long_format(date)}")

    except (TimeoutException, WebDriverException) as e:
        print(f"An error in the web driver occurred!")
        print(str(e))

    finally:
        # Close the browser
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    main()