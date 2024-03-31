# Crossword Scrapper

This is a fun project with the goal of extracting crossword data such as blank pattern distribution, clue analysis, average size of words, dictionary ranking of words, etc. from the nice collection of crosswords at [**El País**](https://elpais.com/juegos/crucigramas). Authors of the crosswords are Nataly Sanoja (Experto and Mini), Mambrino and Tarkus, all credit goes to them for making these excellent puzzles.

The goal is to learn how web scraping works, along with doing some nice data analysis and getting some insights on crossword creation.

## Progress
Web scraper is done, currently working on data exploration, with already some nice results achieved, check the notebook!

## Data exploration
- Heatmap for finding which cells are more common to have grey cells
- Heatmap for finding which cells are more common to be horizontal/vertical word starts (TODO)
- Average word length, average words per crossword (TODO) and other metrics about words
- Most common words for each author
- TF-IDF analysis for finding words unique to each crossword maker
- Explore clue avg. number of words, look for repeated clues in multiple crosswords (TODO)
- Find crossword difficulty metrics, analyzing clue difficulty and other factors like word rarity (TODO)
- Explore crossword seasonality patterns (i.e. specific words for Christmas crosswords) (TODO)

## How to use
1. Download mozilla firefox and setup a custom scraper profile at `profile:addons`
2. Install UBlockOrigin in this profile, to skip unnecesary video ads and make the process faster and more robust
3. Download Gecko Driver executable and place it on the project folder (with name `geckodriver.exe`)
4. Setup the .env variables for the firefox installation, the firefox profile and the gecko driver executable
5. Tweak additional configuration, explained at `settings.py`
6. Preferably, use a VPN just in case your IP gets banned (altough this small number of requests shouldn't be deemed harmful by the server)
7. After collecting the data, run the analysis notebook!

## Data scheme
All data is saved into a `.pkl` with a name specified in `settings.py`, data is saved as a dict with a `(type, date)` key and the following fields for each entry:

- type - The crossword collection type
- date - The date in format YYYY/MM/DD
- layout - A binary matrix with 0s for originally empty cells and 1s for grey cells
- letters - The solution letter matrix, with grey cells represented by '-'
- vclues - The vertical clues text
- vclues_pos - The (x, y) position (0-indexed) of the vertical word starts
- vclues_len - The word lengths of the answers to the vertical clues
- hclues - The horizontal clues text
- hclues_pos - The (x, y) position (0-indexed) of the horizontal word starts
- hclues_len - The word lengths of the answers to the horizontal clues

## Technologies:
- Mozilla Firefox' Gecko Driver, the bot version of mozilla
- Selenium, the web driver adapter that allows us to automatically navigate and click through the pages to handle dynamic content extraction
- BeautifulSoup, to perform some of the HTML scraping
- Pandas, for data analysis and organization
