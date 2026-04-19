from real_estate.scrappers.leboncoin_playwright import scrape_leboncoin
from real_estate.scrappers.seloger_playwright import scrape_seloger
from real_estate.scrappers.cyphoma_playwright import scrape_cyphoma
from real_estate.scrappers.97immo_playwright import scrape_97immo

from .analyzers.yield_calc import calculate_yield
from .analyzers.scoring import score_property
from .analyzers.ai_analysis import analyze_property_ai
from .analyzers.market_estimator import estimate_price_m2
from .analyzers.deal_detector import detect_deal

def get_real_estate_data(zone, budget):

    sources = [
        scrape_leboncoin,
        scrape_seloger,
        scrape_cyphoma,
        scrape_97immo
    ]

    results = []

    for source in sources:
        try:
            data = source(zone, SCRAPER_LIMIT)
            if data:
                results.extend(data)
        except Exception as e:
            print(f"Error {source.__name__}: {e}")

    # parse price
    results = [
        r for r in results
        if parse_price(r["price"]) <= budget
    ]

    return sorted(results, key=lambda x: parse_price(x["price"]))[:20]
    

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

    deals = get_real_estate_opportunities(city, budget)

    scored = []

    for d in deals:
        market_price = d["price"] * 1.2  # approximation V1

        d["score"] = score_deal(d["price"], market_price)

        if d["score"] > 40:
            scored.append(d)

    return sorted(scored, key=lambda x: x["score"], reverse=True)


