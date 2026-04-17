from .providers.market_data import get_crypto_price
from .providers.trending import get_trending_crypto

from .analyzers.ai_analysis import analyze_crypto_ai
from .analyzers.scoring import score_crypto


def get_crypto_intelligence(query):

    try:
        market = get_crypto_price(query.symbol)
        trends = get_trending_crypto()

        trend = next(
            (t["trend"] for t in trends if t["symbol"] == query.symbol.upper()),
            "neutral"
        )

        score = score_crypto(trend, query.strategy)

        ai = analyze_crypto_ai({
            "symbol": query.symbol,
            "price": market.get("price", 0),
            "trend": trend
        })

        return {
            "symbol": query.symbol,
            "price": market.get("price", 0),
            "trend": trend,
            "score": score,
            "ai_analysis": ai
        }

    except Exception as e:
        return {
            "error": str(e),
            "symbol": query.symbol
        }
