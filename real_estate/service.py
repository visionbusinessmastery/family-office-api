from .scrappers.leboncoin import search_leboncoin
from .scrappers.seloger import search_seloger
from .scrappers.ventes_publiques import search_ventes_publiques
from .scrappers.agorastore import search_agorastore
from .scrappers.imodom import search_imodom

from .analyzers.yield_calc import calculate_yield
from .analyzers.scoring import score_property


def get_real_estate_intelligence(query):

    listings = []

    # 🔎 Multi sources
    listings += search_leboncoin(query.city)
    listings += search_seloger(query.city)
    listings += search_ventes_publiques(query.city)
    listings += search_agorastore(query.city)
    listings += search_imodom(query.city)

    results = []

    for prop in listings:

        # 🔒 filtres utilisateur
        if prop["price"] > query.budget:
            continue

        if prop["surface"] < query.surface_min:
            continue

        yield_value = calculate_yield(prop)
        score = score_property(prop, yield_value, query.strategy)

        # 💡 détection opportunité
        deal = "standard"

        if yield_value > 8:
            deal = "good"

        if yield_value > 10 or prop["price"] < 100000:
            deal = "excellent"

        results.append({
            "title": prop["title"],
            "price": prop["price"],
            "surface": prop["surface"],
            "yield": yield_value,
            "score": score,
            "deal": deal,
            "source": prop["source"]
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)
