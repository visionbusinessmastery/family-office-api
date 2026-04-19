from playwright.sync_api import sync_playwright
from real_estate.config import SCRAPER_MATRIX

def get_sources(zone: str):
    return SCRAPER_MATRIX.get(zone, [])
    
def scrape_seloger(city, max_price):

    results = []

    url = f"https://www.seloger.com/list.htm?types=1&locations={city}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        cards = page.query_selector_all("article")

        for card in cards[:20]:

            try:
                title = card.query_selector("h2").inner_text()
                price_text = card.query_selector('[data-testid="price"]').inner_text()

                price = int(price_text.replace("€", "").replace(" ", ""))

                if price <= max_price:

                    results.append({
                        "title": title,
                        "price": price,
                        "source": "seloger"
                    })

            except:
                continue

        browser.close()

    return results
