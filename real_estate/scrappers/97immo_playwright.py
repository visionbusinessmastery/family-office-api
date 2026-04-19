from playwright.sync_api import sync_playwright
from real_estate.config import DOM_TOM_ZONES, SCRAPER_LIMIT, SUPPORTED_REGIONS
  
def scrape_97immo(zone: str, max_results: int = SCRAPER_LIMIT):
    results = []

    if zone not in DOM_TOM_ZONES:
        return []

    url = f"https:/www.97immo.com/{DOM_TOM_ZONES[zone]}/immobilier"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, timeout=60000)
        page.wait_for_timeout(3000)

        annonces = page.query_selector_all("article")[:max_results]

        for annonce in annonces:
            try:
                title = annonce.query_selector("h2").inner_text()
                price = annonce.query_selector(".price").inner_text()
                link = annonce.query_selector("a").get_attribute("href")

                results.append({
                    "title": title,
                    "price": price,
                    "link": f"https://www.97immo.com{link}",
                    "source": "97immo",
                    "zone": zone
                })
            except:
                continue

        browser.close()

    return results
