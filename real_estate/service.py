from .scrappers.leboncoin import search_leboncoin
from .scrappers.seloger import search_seloger
from .scrappers.ventes_publiques import search_ventes_publiques
from .scrappers.agorastore import search_agorastore
from .scrappers.imodom import search_imodom

from .analyzers.yield_calc import calculate_yield
from .analyzers.scoring import score_property
from .analyzers.ai_analysis import analyze_property_ai
from .analyzers.market_estimator import estimate_price_m2
from .analyzers.deal_detector import detect_deal


def get_real_estate_intelligence(query):

    try:
        listings = []

        listings += search_leboncoin(query.city)
        listings += search_seloger(query.city)
        listings += search_ventes_publiques(query.city)
        listings += search_agorastore(query.city)
        listings += search_imodom(query.city)

        results = []

        market_price_m2 = estimate_price_m2(query.city)

        for prop in listings:

            price = prop.get("price", 0)
            surface = prop.get("surface", 0)

            if price > query.budget:
                continue

            if surface < query.surface_min:
                continue

            yield_value = calculate_yield(prop)
            score = score_property(prop, yield_value, query.strategy)

            deal = detect_deal(prop, market_price_m2)
            ai_analysis = analyze_property_ai(prop)

            results.append({
                "title": prop.get("title"),
                "price": price,
                "surface": surface,
                "yield": yield_value,
                "score": score,
                "deal": deal,
                "ai": ai_analysis,
                "source": prop.get("source")
            })

        return sorted(results, key=lambda x: x["score"], reverse=True)

    except Exception as e:
        return {
            "error": str(e)
        }
