from .scrappers.leboncoin import search_leboncoin
from .scrappers.seloger import search_seloger
from .scrappers.ventes_publiques import search_ventes_publiques
from .scrappers.imodom import search_imodom
from .scrappers.agorastore import search_agorastore

from ..analyzers.yield import calculate_yield
from ..analyzers.scoring import score_property
from ..analyzers.ai_analysis import analyze_property_ai


def get_real_estate_intelligence(query):

    listings = []

    listings += search_leboncoin(query.city)
    listings += search_seloger(query.city)
    listings += search_ventes_publiques(query.city)
    listings += search_imodom(query.city)
    listings += search_agorastore(query.city)

    results = []

    for property in listings:

        yield_value = calculate_yield(property)
        score = score_property(property, yield_value, query.strategy)

        ai_insight = analyze_property_ai(property)

        results.append({
            "title": property["title"],
            "price": property["price"],
            "surface": property["surface"],
            "yield": yield_value,
            "score": score,
            "ai_analysis": ai_insight,
            "source": property.get("source", "unknown")
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)
