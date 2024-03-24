# Crossword Scrapper

This is a fun project with the goal of extracting crossword data such as blank pattern distribution, clue analysis, average size of words, dictionary ranking of words, etc. from the nice collection of crosswords at [**El País**](https://elpais.com/juegos/crucigramas).

The goal is to learn how web scraping works, along with doing some nice data analysis and getting some insights on crossword creation.

## How to use
1. Download mozilla firefox and setup a custom scraper profile at *profile:addons*
2. Install UBlockOrigin in this profile, to skip unnecesary video ads and make the process faster and more robust
3. Download Gecko Driver executable
4. Setup the .env variables for the firefox installation, the firefox profile and the gecko driver executable
5. Tweak additional configuration, explained at *settings.py*
6. Enjoy!

## Technologies used:
- Mozilla Firefox' Gecko Driver, the bot version of mozilla
- Selenium, the web driver adapter that allows us to automatically navigate and click through the pages to handle dynamic content extraction
- BeautifulSoup, to perform the HTML scraping
- Pandas, for data analysis and organization