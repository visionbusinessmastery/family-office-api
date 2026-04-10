from .scrapers.leboncoin import search_leboncoin
from .analyzers.yield_calc import calculate_yield
from .analyzers.scoring import score_property


def get_real_estate_intelligence(query):

    listings = search_leboncoin(query.city)

    results = []

    for property in listings:

        yield_value = calculate_yield(property)
        score = score_property(property, yield_value, query.strategy)

        results.append({
            "title": property["title"],
            "price": property["price"],
            "surface": property["surface"],
            "yield": yield_value,
            "score": score,
            "source": property["source"]
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)
