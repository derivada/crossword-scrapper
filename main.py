from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from settings import FIREFOX_PATH, FIREFOX_PROFILE_PATH, RUN_HEADLESS, CROSSWORD_COLLECTION
from tqdm import tqdm
from utils import *
import numpy as np
import matplotlib.pyplot as plt

# First visualization, a dynamic heatmap showing the most common spots for gray cells
def plot_heatmap(matrix, last_it, total_crosswords):
    plt.clf()  # Clear the current figure
    plt.imshow(matrix, cmap='gray_r', interpolation='nearest')
    plt.colorbar()
    plt.title(f'Heatmap de celdas grises en crucigramas {CROSSWORD_COLLECTION.capitalize()}, crucigramas vistos: {total_crosswords}')
    word_length_avg = np.mean(np.array(words))
    plt.text(1, -1.5, f"Longitud palabra media: {word_length_avg:.2f}", fontsize=12, ha='center')
    if not last_it:
        plt.pause(0.1)
        plt.draw()
    else:
        plt.show()

sum_matrix = None
words = []
total_crosswords = 0

def scrape_crossword(crossword_html, last_it):
    global sum_matrix, total_crosswords
    # We scrape the data using beautiful soup
    soup = BeautifulSoup(crossword_html, "lxml")
    grid = soup.find(class_="crossword")
    rows = [[]]; row = 0
    for div in grid.find_all('div', recursive=False):
        # letters
        if 'class' in div.attrs and 'endRow' in div['class']:
            row += 1
            rows.append([])
        elif 'class' in div.attrs and 'prerevealed-box' not in div['class']:
            rows[row].append(0 if div.find('span') else 1)
    
    # Last row is empty and gets deleted, first row may also be empty (in mambrinus and tarkus because of first col numbers in the top)
    del rows[-1]
    if len(rows[0]) == 0:
        del rows[0] 
    matrix = np.array(rows)

    # Get the average word length
    curr_len = 0

    # TODO fix, this takes into account horizontal strips of length 1 that are words (they appear in mambrino/tarkus), should use clue info
    # Horizontal words
    for i in range(0, matrix.shape[0]):
        for j in range(0, matrix.shape[1]):
            if(matrix[i, j] == 0):
                curr_len += 1
            elif curr_len > 1:
                words.append(curr_len)
                curr_len = 0
        if curr_len > 1:
            words.append(curr_len)
        curr_len = 0
    # Vertical words
    for j in range(0, matrix.shape[0]-1):
        for i in range(0, matrix.shape[1]-1):
            if(matrix[i, j] == 0):
                curr_len += 1
            elif curr_len > 1:
                words.append(curr_len)
                curr_len = 0
        if curr_len > 1:
            words.append(curr_len)
        curr_len = 0

    if sum_matrix is None:
        sum_matrix = matrix
    else:
        sum_matrix += matrix
    print(sum_matrix)
    total_crosswords += 1
    normalized_matrix = sum_matrix / total_crosswords
    plot_heatmap(normalized_matrix, last_it, total_crosswords)


def main():
    driver = None
    start_date = "20230102"
    end_date = "20230110"
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
            url = f'https://elpais.com/juegos/crucigramas/{CROSSWORD_COLLECTION}/?id=elpais-{CROSSWORD_COLLECTION}_{date}_0300'
            driver.get(url)

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