from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from settings import *
from tqdm import tqdm
from utils import *
import numpy as np
import pickle
import traceback

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

def mini_experto_extract_words_info(soup, layout):
    crossword_shape = np.shape(layout)
    hor_clues_html = soup.find(class_="aclues")
    ver_clues_html = soup.find(class_="dclues")
    vclues_pos = []; vclues_len = []; hclues_pos = []; hclues_len = []
    
    # First find which markers are horizontal and which ones are vertical
    hclues_n = np.array([int(element.string) for element in hor_clues_html.find_all(class_='clueNum')])
    vclues_n = np.array([int(element.string) for element in ver_clues_html.find_all(class_='clueNum')])
    grid = soup.find(class_="crossword")
    i = 0
    for div in grid.find_all('div', recursive=False):
        if 'class' in div.attrs and 'endRow' in div['class']:
            continue
        cluenum = div.find('span', class_='cluenum-in-box')
        if cluenum != None:
            clue_n = int(''.join(filter(str.isdigit, cluenum.text))) # Remove Unicode non numeric characters
            coords = (i // crossword_shape[0], i % crossword_shape[0])
            # Find its length by following the clue until the end of the crossword
            len = 0
            if clue_n in hclues_n:
                # Horizontal
                while coords[1] + len < crossword_shape[1] and layout[coords[0]][coords[1] + len] == 0:
                    len += 1
                # Save data into the arrays
                hclues_pos.append(coords)
                hclues_len.append(len)
            if clue_n in vclues_n:
                # Vertical
                while coords[0] + len < crossword_shape[0] and layout[coords[0] + len][coords[1]] == 0:
                    len += 1
                vclues_pos.append(coords)
                vclues_len.append(len)
        i += 1
    return (np.array(hclues_pos), np.array(hclues_len), np.array(vclues_pos), np.array(vclues_len))

def mambrino_tarkus_find_number_clues_direction(clues_html):
    # Find number of words per horizontal
    nclues = []
    i = 0; counter = 0
    for clue in clues_html.find_all(class_="clueDiv"):
        text = clue.find(class_="clueNum").text
        if(text.isdigit()):
            if(i >= 1):
                nclues.append(counter)
            i = int(text)
            counter = 1
        else:
            counter += 1
    nclues.append(counter)
    return np.array(nclues)

def mambrino_tarkus_extract_words_info(driver, soup, layout):
    vclues_pos = []; vclues_len = []; hclues_pos = []; hclues_len = []
    crossword_shape = np.shape(layout)

    # Find number of clues per horizontal / vertical
    nclues_h = mambrino_tarkus_find_number_clues_direction(soup.find(class_="aclues"))
    nclues_v = mambrino_tarkus_find_number_clues_direction(soup.find(class_="dclues"))
    # Horizontals
    for i in range(0, crossword_shape[0]):
        j = 0
        found_words = 0
        while j < crossword_shape[1]:
            if(layout[i][j] == 0):
                found_words += 1
                hclues_pos.append((i, j))
                len = 0
                while(j < crossword_shape[1] and layout[i][j] == 0):
                    len += 1
                    j += 1
                hclues_len.append(len)
            else:
                j+=1
        # If we didnt reach enough words, it is because some 1-letter words are not in the clue list 
        # ( I hate this edge case but we need to ensure that the size of the clue list is the same as the size of the coordinates / lengths of the words for analysis )
        if(nclues_h[i] < found_words):
            # print("EDGE CASE AT ROW ", i)
            # Solve the edge case via the old algorithm of clicking
            # Remove wrong data
            hclues_pos = hclues_pos[:-found_words]
            hclues_len = hclues_len[:-found_words]
            
            # Find the clue divs to be clicked
            clue_list_div = driver.find_element(By.CSS_SELECTOR, '.aclues .clue-list')
            inCol = False
            counter = 0
            for clue in clue_list_div.find_elements(By.CSS_SELECTOR, '.clueDiv'):
                text = str(clue.find_element(By.CSS_SELECTOR, '.clueNum').text)
                if((text.isdigit() and int(text) == i+1) or (inCol and not text.isdigit())):
                    driver.execute_script("arguments[0].scrollIntoView();", clue)
                    clue.click()
                    inCol = True
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.hilited-box-with-focus')))
                    length = 0
                    position = None
                    crossword_html = driver.find_element(By.CSS_SELECTOR, '.puzzle-type-crossword').get_attribute('outerHTML')
                    soup_updated = BeautifulSoup(crossword_html, "lxml")
                    grid = soup_updated.find(class_="crossword")
                    filtered_children = [child for child in grid.children if child.name == 'div' and 'prevealed-box' not in child.get('class', []) and 'endRow' not in child.get('class', [])]
                    for j, child in enumerate(filtered_children):
                        classes = child.get('class', [])
                        if 'hilited-box-with-focus' in classes:
                            position = (j // crossword_shape[0] - 1, j % crossword_shape[0] - 1)
                            length += 1
                        elif 'hilited-box' in classes:
                            length += 1
                    counter += 1
                    hclues_pos.append(position)
                    hclues_len.append(length)
                elif((text.isdigit() and int(text) != i+1)):
                    inCol = False
            assert(counter == nclues_h[i])
    
    # Transpose and repeat for verticals
    layout_t = np.transpose(layout)
    crossword_shape = np.shape(layout_t)
    for i in range(0, crossword_shape[0]):
        j = 0
        found_words = 0
        while j < crossword_shape[1]:
            if(layout_t[i][j] == 0):
                vclues_pos.append((j, i)) # Original coordinates before transposing
                found_words += 1
                len = 0
                while(j < crossword_shape[1] and layout_t[i][j] == 0):
                    len += 1
                    j += 1
                vclues_len.append(len)
            else:
                j+=1
        # Mega repeat of code, TODO fix when I have time
        if(nclues_v[i] < found_words):
            # print("EDGE CASE AT COLUMN ", i)
            # Solve the edge case via the old algorithm of clicking
            # Remove wrong data
            vclues_pos = vclues_pos[:-found_words]
            vclues_len = vclues_len[:-found_words]
            
            # Find the clue divs to be clicked
            clue_list_div = driver.find_element(By.CSS_SELECTOR, '.dclues .clue-list')
            inCol = False
            counter = 0
            for clue in clue_list_div.find_elements(By.CSS_SELECTOR, '.clueDiv'):
                text = str(clue.find_element(By.CSS_SELECTOR, '.clueNum').text)
                if((text.isdigit() and int(text) == i+1) or (inCol and not text.isdigit())):
                    driver.execute_script("arguments[0].scrollIntoView();", clue)
                    clue.click()
                    inCol = True
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.hilited-box-with-focus')))
                    length = 0
                    position = None
                    crossword_html = driver.find_element(By.CSS_SELECTOR, '.puzzle-type-crossword').get_attribute('outerHTML')
                    soup_updated = BeautifulSoup(crossword_html, "lxml")
                    grid = soup_updated.find(class_="crossword")
                    filtered_children = [child for child in grid.children if child.name == 'div' and 'prevealed-box' not in child.get('class', []) and 'endRow' not in child.get('class', [])]
                    for j, child in enumerate(filtered_children):
                        classes = child.get('class', [])
                        if 'hilited-box-with-focus' in classes:
                            position = (j // crossword_shape[1] - 1, j % crossword_shape[1] - 1)
                            length += 1
                        elif 'hilited-box' in classes:
                            length += 1
                    counter += 1
                    vclues_pos.append(position)
                    vclues_len.append(length)
                elif((text.isdigit() and int(text) != i+1)):
                    inCol = False
            assert(counter == nclues_v[i])
    return (np.array(hclues_pos), np.array(hclues_len), np.array(vclues_pos), np.array(vclues_len))

""" 
def general_extract_words_info(driver, clue_list_div):
    positions = []
    lengths = []
    crossword_html = driver.find_element(By.CSS_SELECTOR, '.puzzle-type-crossword').get_attribute('outerHTML')
    soup_updated = BeautifulSoup(crossword_html, "lxml")
    grid = soup_updated.find(class_="crossword")
    filtered_children = [child for child in grid.children if child.name == 'div' and 'prevealed-box' not in child.get('class', []) and 'endRow' not in child.get('class', [])]
    dim = int(np.sqrt(len(filtered_children))) # Assuming square crossword
    for clue_div in clue_list_div.find_elements(By.CSS_SELECTOR, '.clueDiv'):
        print(clue_div.text)
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
        print(position, length)
        positions.append([position])
        lengths.append([length])
         
    return (np.array(positions), np.array(lengths))
"""

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
            # print(date)
            type = CROSSWORD_COLLECTION
            if((type, date) in data_dict): # Already on data CSV
                # print(f'Data already found for type {type} on date {date}')
                continue
            if((type, date) in SKIP): # Special case, skip
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
                crossword = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.puzzle-type-crossword')))
                WebDriverWait(crossword, 1).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.box')))
            except TimeoutException:
                # Invalid crossword URL
                continue
            
            crossword_html = crossword.get_attribute('outerHTML')

            # Get the unrevealed crossword data
            soup = BeautifulSoup(crossword_html, "lxml")
            layout = get_crossword_layout(soup, False)

            # Get the clue texts, along with (x, y) positions and word lengths, we use different algorithms depending on category
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.aclues')))
            hor_clues_html = soup.find(class_="aclues")
            ver_clues_html = soup.find(class_="dclues")
            hclues = np.array([str(element.string) for element in hor_clues_html.find_all(class_='clueText')])
            vclues = np.array([str(element.string) for element in ver_clues_html.find_all(class_='clueText')])
            # Get the start of the word (x,y) position and its length 

            (hclues_len, hclues_len, vclues_pos, vclues_len) = (None, None, None, None)
            if CROSSWORD_COLLECTION in ["experto", "mini"]:
                # Experto algorithm: find the position of the number markers
                (hclues_pos, hclues_len, vclues_pos, vclues_len) = mini_experto_extract_words_info(soup, layout)
            elif CROSSWORD_COLLECTION in ["mambrino", "tarkus"]:
                # Mambrino and Tarkus algorithm: go over each row skipping the grey cells and putting into words the other,
                # Mambrino and Tarkus never leave a 1 word cell empty without a word, like Experto author sometimes does
                (hclues_pos, hclues_len, vclues_pos, vclues_len) = mambrino_tarkus_extract_words_info(driver, soup, layout)
            else:
                print("TODO needs fix, coordinates dont update correctly in each iteration, however this algorithm is not needed for the 3 specified categories, it is old")
                # General algorithm: works for all types, but its very slow since it needs to click every clue to find the start and length of the word
                """
                clue_list_div = driver.find_element(By.CSS_SELECTOR, '.aclues .clue-list')
                hclues_pos, hclues_len = general_extract_words_info(driver, clue_list_div)
                clue_list_div = driver.find_element(By.CSS_SELECTOR, '.dclues .clue-list')
                vclues_pos, vclues_len = general_extract_words_info(driver, clue_list_div)
                print(hclues_pos, hclues_len, vclues_pos, vclues_len)
                """
            assert(np.shape(hclues)[0] == np.shape(hclues_len)[0] == np.shape(hclues_pos)[0])
            assert(np.shape(vclues)[0] == np.shape(vclues_len)[0] == np.shape(vclues_pos)[0])
            # Reveal the solution and get statitics about the letters
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[title="Revelar"]'))).click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.reveal-all-button > a'))).click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.confirm-yes'))).click()
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.close'))).click()

            # Get the parent crossword element
            crossword = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.crossword')))
            WebDriverWait(crossword, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.box')))
            crossword_html = crossword.get_attribute('outerHTML')

            # Get the unrevealed crossword data
            soup = BeautifulSoup(crossword_html, "lxml")
            letters = get_crossword_layout(soup, True)
            
            # Insert into big dict
            row_data = {'type': type, 'date': date, 'layout': layout, 'hclues': hclues, 'vclues': vclues, 'vclues_pos': vclues_pos, 
                        'vclues_len': vclues_len, 'hclues_pos': hclues_pos, 'hclues_len': hclues_len, 'letters': letters}
            data_dict[(type, date)] = row_data
            # Save data to file every 10 iterations. This is not 100% efficient since we are saving the entire dict in each iteration,
            # but it is better than the program crashing and losing all data
            if i % 10 == 9:
                with open(DATA_FILE, 'wb') as f:
                    pickle.dump(data_dict, f)
        # Save final chunks of data
        with open(DATA_FILE, 'wb') as f:
            pickle.dump(data_dict, f)
    except Exception as e:
        print(f"An error in the web driver occurred!")
        print(str(e))
        print(f"Last date: {date} on category {CROSSWORD_COLLECTION}")
        print("STACKTRACE:")
        traceback.print_exc()
    finally:
        # Close the browser
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    main()