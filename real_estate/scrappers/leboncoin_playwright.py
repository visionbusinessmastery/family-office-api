from playwright.sync_api import sync_playwright
from real_estate.config import ZONES, SCRAPER_LIMIT, SUPPORTED_REGIONS
    
def scrape_leboncoin(city, max_price):

    results = []

    url = f"https://www.leboncoin.fr/recherche?category=9&text={city}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        listings = page.query_selector_all('[data-qa-id="aditem_container"]')

        for item in listings[:20]:

            try:
                title = item.query_selector('[data-qa-id="aditem_title"]').inner_text()
                price_text = item.query_selector('[data-qa-id="aditem_price"]').inner_text()

                price = int(price_text.replace("€", "").replace(" ", ""))

                if price <= max_price:

                    results.append({
                        "title": title,
                        "price": price,
                        "source": "leboncoin"
                    })

            except:
                continue

        browser.close()

    return results
