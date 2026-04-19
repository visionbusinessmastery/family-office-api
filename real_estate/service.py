import re

from real_estate.config import SCRAPER_LIMIT
from real_estate.scrappers.cyphoma_playwright import scrape_cyphoma
from real_estate.scrappers.immo97_playwright import scrape_97immo
from real_estate.scrappers.leboncoin_playwright import scrape_leboncoin
from real_estate.scrappers.seloger_playwright import scrape_seloger


def parse_price(raw_price):
    if isinstance(raw_price, (int, float)):
        return float(raw_price)

    if not raw_price:
        return 0.0

    cleaned = re.sub(r"[^0-9]", "", str(raw_price))
    return float(cleaned) if cleaned else 0.0


def get_real_estate(zone, budget):
    results = []

    sources = [
        lambda: scrape_leboncoin(zone, budget),
        lambda: scrape_seloger(zone, budget),
        lambda: scrape_cyphoma(zone, SCRAPER_LIMIT),
        lambda: scrape_97immo(zone, SCRAPER_LIMIT),
    ]

    for source in sources:
        try:
            data = source()
            if data:
                results.extend(data)
        except Exception as e:
            print(f"Error during scraping: {e}")

    results = [r for r in results if parse_price(r.get("price")) <= budget]

    return sorted(results, key=lambda x: parse_price(x.get("price")))[:20]


def score_property(price, budget):
    return round((budget - price) / budget * 100)


def score_deal(price, market_price):
    discount = (market_price - price) / market_price

    score = 0

    if discount > 0.3:
        score += 50
    elif discount > 0.15:
        score += 30
    else:
        score += 10

    return min(score, 100)


def deal_finder(city, budget):
    deals = get_real_estate(city, budget)

    scored = []

    for d in deals:
        market_price = parse_price(d.get("price")) * 1.2  # approximation V1
        price = parse_price(d.get("price"))
        d["score"] = score_deal(price, market_price)

        if d["score"] > 40:
            scored.append(d)

    return sorted(scored, key=lambda x: x["score"], reverse=True)


def get_real_estate_intelligence(city, budget):
    deals = get_real_estate(city, budget)

    enriched = []

    for d in deals:
        try:
            price = parse_price(d.get("price"))
            d["score"] = score_property(price, budget)
            d["deal_score"] = score_deal(price, price * 1.2)
            enriched.append(d)
        except Exception:
            continue

    return enriched


