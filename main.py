from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from settings import FIREFOX_PATH, FIREFOX_PROFILE_PATH, DATA_PATH, RUN_HEADLESS, CROSSWORD_COLLECTION
from tqdm import tqdm
from utils import *
from time import sleep
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
import pickle

class RowData:
    def __init__(self, type, date, layout, hclues, vclues, vclues_pos, vclues_len, hclues_pos, hclues_len, letters):
        self.type = type
        self.date = date
        self.layout = layout
        self.hclues = hclues
        self.vclues = vclues
        self.vclues_pos = vclues_pos
        self.vclues_len = vclues_len
        self.hclues_pos = hclues_pos
        self.hclues_len = hclues_len
        self.letters = letters

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

# Returns the layout of the crossword as a binary numpy matrix, from the unreveled crossword HTML soup element
def get_crossword_layout(soup, revealed):
    grid = soup.find(class_="crossword")
    rows = [[]]; row = 0
    for div in grid.find_all('div', recursive=False):
        # letters
        if 'class' in div.attrs and 'endRow' in div['class']:
            row += 1
            rows.append([])
        elif 'class' in div.attrs and 'prerevealed-box' not in div['class']:
            if(revealed):
                rows[row].append(div.find('span', class_='letter-in-box').string if div.find('span', class_='letter-in-box') else '-')
            else:
                rows[row].append(0 if div.find('span') else 1)
    
    # Last row is empty and gets deleted, first row may also be empty (in mambrinus and tarkus because of first col numbers in the top)
    del rows[-1]
    if len(rows[0]) == 0:
        del rows[0] 
    
    return np.array(rows)


def extract_clues_len_and_pos(driver, clue_list_div):
    positions = []
    lengths = []
    for clue_div in clue_list_div.find_elements(By.CSS_SELECTOR, '.clueDiv'):
        driver.execute_script("arguments[0].scrollIntoView();", clue_div)
        clue_div.click()
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.hilited-box-with-focus')))
        # Find position and length of the word
        crossword_html = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.puzzle-type-crossword'))).get_attribute('outerHTML')
        soup_updated = BeautifulSoup(crossword_html, "lxml")
        grid = soup_updated.find(class_="crossword")
        filtered_children = [child for child in grid.children if child.name == 'div' and 'prevealed-box' not in child.get('class', []) and 'endRow' not in child.get('class', [])]
        dim = int(np.sqrt(len(filtered_children))) # Assuming square crossword
        length = 0; position = None
        for i, child in enumerate(filtered_children):
            classes = child.get('class', [])
            if 'hilited-box-with-focus' in classes:
                position = (i // dim, i % dim)
                length += 1
            elif 'hilited-box' in classes:
                length += 1
        positions.append([position])
        lengths.append([length])
    return (np.array(positions), np.array([lengths]))

def main():
    driver = None
    start_date = "20230102"
    end_date = "20230102"
    date_list = date_range(start_date, end_date)
    try:
        with open('data.pkl', 'rb') as f:
            loaded_data = pickle.load(f)
        data_dict = loaded_data
    except FileNotFoundError:
        data_dict = {}
        print("Data file not found. Initializing an empty data dictionary.")
    
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
            if((CROSSWORD_COLLECTION, date) in data_dict): # Already on data CSV
                print(f'Data already found for type {CROSSWORD_COLLECTION} on date {date}')
                continue
            new_row = {'type': CROSSWORD_COLLECTION, 'date': date}
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
            
            crossword_html = crossword.get_attribute('outerHTML')

            # Get the unrevealed crossword data
            soup = BeautifulSoup(crossword_html, "lxml")
            sleep(2)
            new_row['layout'] = get_crossword_layout(soup, False)

            # Get the clue text, along with (x, y) positions and word lengths
            # horizontal
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.aclues')))
            hor_clues_html = soup.find(class_="aclues")
            new_row['hclues'] = np.array([element.string for element in hor_clues_html.find_all(class_='clueText')])
            ver_clues_html = soup.find(class_="dclues")
            new_row['vclues'] = np.array([element.string for element in ver_clues_html.find_all(class_='clueText')])


            # Click on every clue to get the length of the word and its starting position
            new_row['vclues_pos'] = []; new_row['vclues_len'] = []; new_row['hclues_pos'] = []; new_row['hclues_len'] = []
            # Horizontals
            clue_list_div = driver.find_element(By.CSS_SELECTOR, '.aclues .clue-list')
            new_row['hclues_pos'], new_row['hclues_len'] = extract_clues_len_and_pos(driver, clue_list_div)
            # Verticals
            clue_list_div = driver.find_element(By.CSS_SELECTOR, '.dclues .clue-list')
            new_row['vclues_pos'], new_row['vclues_len'] = extract_clues_len_and_pos(driver, clue_list_div)

            # Reveal the solution and get statitics about the letters
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[title="Revelar"]'))).click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.reveal-all-button > a'))).click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.confirm-yes'))).click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.close'))).click()

            # Get the parent crossword element
            crossword = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.puzzle-type-crossword')))
            crossword_html = crossword.get_attribute('outerHTML')

            # Get the unrevealed crossword data
            soup = BeautifulSoup(crossword_html, "lxml")
            new_row['letters'] = get_crossword_layout(soup, True)

            for column, value in new_row.items():
                print(f"{column}: {type(value)}")
                print(value)
                print("\n---\n")
            
            row_data = RowData(new_row['type'],  new_row['date'], new_row['layout'], new_row['hclues'], new_row['vclues'],
                     new_row['vclues_pos'], new_row['vclues_len'], new_row['hclues_pos'], new_row['hclues_len'], new_row['letters'])

            data_dict[(new_row['type'],  new_row['date'])] = row_data

        with open('data.pkl', 'wb') as f:
            pickle.dump(data_dict, f)
            

    except (TimeoutException, WebDriverException) as e:
        print(f"An error in the web driver occurred!")
        print(str(e))

    finally:
        # Close the browser
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    main()