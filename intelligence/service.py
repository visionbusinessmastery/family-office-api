from real_estate.service import get_real_estate_intelligence
from crypto.service import get_crypto_intelligence
from stocks.service import get_stock_intelligence

from .analyzers.allocation import allocate_portfolio
from .analyzers.ai_global import global_ai_analysis


# 🔥 NORMALISATION DU RISQUE (AJOUT)
def normalize_risk(risk: str):

    if not risk:
        return "modéré"

    r = risk.lower().strip()

    mapping = {
        "faible": "faible",
        "low": "faible",

        "modéré": "modéré",
        "modere": "modéré",
        "medium": "modéré",

        "élevé": "élevé",
        "eleve": "élevé",
        "high": "élevé"
    }

    return mapping.get(r, "modéré")


def get_global_intelligence(query):

    try:
        # 🔥 FIX ICI
        risk = normalize_risk(query.risk)

        # 🔹 REAL ESTATE
        real_data = get_real_estate_intelligence(query.city, query.budget)

        # 🔹 CRYPTO
        crypto_data = get_crypto_intelligence(
            type("obj", (), {
                "symbol": "BTC",
                "strategy": "long_term"
            })
        )

        # 🔹 STOCKS
        stock_data = get_stock_intelligence(
            type("obj", (), {
                "symbol": "AAPL",
                "strategy": "long_term"
            })
        )

        # 🔥 on passe le bon risk
        query.risk = risk

        allocation = allocate_portfolio(query, real_data, crypto_data, stock_data)

        ai = global_ai_analysis({
            "budget": query.budget,
            "risk": risk,
            "allocation": allocation
        })

        return {
            "real_estate": real_data[:3] if isinstance(real_data, list) else [],
            "crypto": crypto_data,
            "stocks": stock_data,
            "allocation": allocation,
            "ai_global": ai
        }

    except Exception as e:
        return {
            "error": str(e)
        }
