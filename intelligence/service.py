from real_estate.service import get_real_estate_intelligence
from crypto.service import get_crypto_intelligence
from stocks.service import get_stock_intelligence

from .analyzers.allocation import allocate_portfolio
from .analyzers.ai_global import global_ai_analysis


def get_global_intelligence(query):

    # 🔹 Simulations (MVP)
    real_data = get_real_estate_intelligence(
        type("obj", (), {
            "city": "paris",
            "budget": query.budget,
            "surface_min": 20,
            "strategy": "rent"
        })
    )

    crypto_data = get_crypto_intelligence(
        type("obj", (), {
            "symbol": "BTC",
            "strategy": "long_term"
        })
    )

    stock_data = get_stock_intelligence(
        type("obj", (), {
            "symbol": "AAPL",
            "strategy": "long_term"
        })
    )

    allocation = allocate_portfolio(query, real_data, crypto_data, stock_data)

    ai = global_ai_analysis({
        "budget": query.budget,
        "risk": query.risk,
        "allocation": allocation
    })

    return {
        "real_estate": real_data[:3],
        "crypto": crypto_data,
        "stocks": stock_data,
        "allocation": allocation,
        "ai_global": ai
    }
