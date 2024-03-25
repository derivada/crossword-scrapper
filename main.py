from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from settings import FIREFOX_PATH, FIREFOX_PROFILE_PATH, RUN_HEADLESS
from tqdm import tqdm
from utils import *
import numpy as np
import matplotlib.pyplot as plt

def plot_heatmap(matrix, last_it):
    plt.clf()  # Clear the current figure
    plt.imshow(matrix, cmap='gray_r', interpolation='nearest')
    plt.colorbar()
    plt.title('Heatmap de celdas grises en crucigramas de Mambrino')
    if not last_it:
        plt.pause(0.1)
        plt.draw()
    else:
        plt.show()

sum_matrix = None
def scrape_crossword(crossword_html, last_it):
    global sum_matrix
    # We scrape the data using beautiful soup
    soup = BeautifulSoup(crossword_html, "lxml")
    grid = soup.find(class_="crossword")
    rows = []; row = -1
    for div in grid.find_all('div', recursive=False):
        # letters
        if 'class' in div.attrs and 'endRow' in div['class']:
            row += 1
            rows.append([])
        elif 'class' in div.attrs and 'prerevealed-box' not in div['class']:
            rows[row].append(0 if div.find('span') else 1)
    
    # Last row is empty and gets deleted
    del rows[-1]
    matrix = np.array(rows)
    if sum_matrix is None:
        sum_matrix = matrix
    else:
        sum_matrix += matrix
    normalized_matrix = sum_matrix / np.max(sum_matrix)
    plot_heatmap(normalized_matrix, last_it)

def main():
    driver = None
    start_date = "20230102"
    end_date = "20230120"
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
        for i, date in enumerate(pbar):
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
            # Additionally check at least a cell has been loaded
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.box')))
            crossword_html = crossword.get_attribute('outerHTML')
            scrape_crossword(crossword_html, last_it = True if i == len(date_list)-1 else False)
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