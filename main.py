from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from settings import *
from tqdm import tqdm
from utils import *
from time import sleep
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import pickle
import copy

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
    crossword_html = driver.find_element(By.CSS_SELECTOR, '.puzzle-type-crossword').get_attribute('outerHTML')
    soup_updated = BeautifulSoup(crossword_html, "lxml")
    grid = soup_updated.find(class_="crossword")
    filtered_children = [child for child in grid.children if child.name == 'div' and 'prevealed-box' not in child.get('class', []) and 'endRow' not in child.get('class', [])]
    dim = int(np.sqrt(len(filtered_children))) # Assuming square crossword
    
    for clue_div in clue_list_div.find_elements(By.CSS_SELECTOR, '.clueDiv'):
        driver.execute_script("arguments[0].scrollIntoView();", clue_div)
        clue_div.click()
        
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.hilited-box-with-focus')))
        
        length = 0
        position = None
        
        for i, child in enumerate(filtered_children):
            classes = child.get('class', [])
            if 'hilited-box-with-focus' in classes:
                position = (i // dim, i % dim)
                length += 1
            elif 'hilited-box' in classes:
                length += 1
        
        positions.append([position])
        lengths.append([length])
        
    return (np.array(positions), np.array(lengths))

def setup_browser():
    options = webdriver.FirefoxOptions()
    if(RUN_HEADLESS):
        options.add_argument('--headless')
    profile = webdriver.FirefoxProfile(FIREFOX_PROFILE_PATH)
    driver = webdriver.Firefox(firefox_binary=FIREFOX_PATH, executable_path="geckodriver.exe", options=options, firefox_profile=profile)
    return driver

def main():
    driver = None 

    # Try opening the saved data file to not repeat work, if it doesn't exist start from zero
    try:
        with open(DATA_FILE, 'rb') as f:
            loaded_data = pickle.load(f)
        data_dict = loaded_data
        print(f"Found existing data with {len(data_dict)} entries")
        print(f"Approximate size of loaded data: {data_size(data_dict)}")
    except FileNotFoundError:
        data_dict = {}
        print("Data file not found. Initializing an empty data dictionary.")
    
    try:
        driver = setup_browser()
        
        acceptedCookies = False
        pbar = tqdm(date_range(START_DATE, END_DATE))
        for i, date in enumerate(pbar):
            type = CROSSWORD_COLLECTION
            if((type, date) in data_dict): # Already on data CSV
                print(f'Data already found for type {type} on date {date}')
                continue
            # Open page
            url = f'https://elpais.com/juegos/crucigramas/{CROSSWORD_COLLECTION}/?id=elpais-{CROSSWORD_COLLECTION}_{date}_0300'
            driver.get(url)

            # Cookie consent needs to be given in first iteration
            if not acceptedCookies:
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
            try:
                sleep(1)
                crossword = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.puzzle-type-crossword')))
            except TimeoutException:
                # Invalid crossword URL
                continue
            
            crossword_html = crossword.get_attribute('outerHTML')

            # Get the unrevealed crossword data
            soup = BeautifulSoup(crossword_html, "lxml")
            layout = get_crossword_layout(soup, False)

            # Get the clue texts, along with (x, y) positions and word lengths
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.aclues')))
            hor_clues_html = soup.find(class_="aclues")
            hclues = np.array([str(element.string) for element in hor_clues_html.find_all(class_='clueText')])
            ver_clues_html = soup.find(class_="dclues")
            vclues = np.array([str(element.string) for element in ver_clues_html.find_all(class_='clueText')])
 
            # Click on every clue to get the length of the word and its starting position
            # This step is the slowest, comment if not needed
            # Horizontals
            clue_list_div = driver.find_element(By.CSS_SELECTOR, '.aclues .clue-list')
            hclues_pos, hclues_len = extract_clues_len_and_pos(driver, clue_list_div)
            # Verticals
            clue_list_div = driver.find_element(By.CSS_SELECTOR, '.dclues .clue-list')
            vclues_pos, vclues_len = extract_clues_len_and_pos(driver, clue_list_div)

            # Reveal the solution and get statitics about the letters
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[title="Revelar"]'))).click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.reveal-all-button > a'))).click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.confirm-yes'))).click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.close'))).click()

            # Get the parent crossword element
            sleep(1)
            crossword = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.crossword')))
            crossword_html = crossword.get_attribute('outerHTML')

            # Get the unrevealed crossword data
            soup = BeautifulSoup(crossword_html, "lxml")
            letters = get_crossword_layout(soup, True)
            
            # Insert into big dict
            row_data = {'type': type, 'date': date, 'layout': layout, 'hclues': hclues, 'vclues': vclues, 'vclues_pos': vclues_pos, 
                        'vclues_len': vclues_len, 'hclues_pos': hclues_pos, 'hclues_len': hclues_len, 'letters': letters}
            data_dict[(type, date)] = row_data
            # Save data to file. This is unefficient since we are saving the entire dict in each iteration,
            # but it is better than the program crashing and losing all data
            with open(DATA_FILE, 'wb') as f:
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