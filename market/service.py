import requests
import os
from config import FMP_API_KEY
from openai import OpenAI
from market.sentiment import analyze_sentiment
from market.trends import get_trends
from market.scoring import calculate_ai_score, get_signal, get_risk

FMP_API_KEY = os.getenv("FMP_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_market_news(ticker):

    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={ticker}&limit=5&apikey={FMP_API_KEY}"
    
    try:
        res = requests.get(url)
        data = res.json()
        return data
    except:
        return []


def get_market_intelligence(query: str):
    """
    Fonction simple qui récupère des infos marché (version MVP)
    """

    sources = [
        f"https://www.boursorama.com/recherche/?query={query}",
        f"https://www.zonebourse.com/recherche/?q={query}",
        f"https://www.investing.com/search/?q={query}"
    ]

    results = []

    for url in sources:
        try:
            response = requests.get(url, timeout=5)
            results.append({
                "source": url,
                "status": response.status_code
            })
        except Exception as e:
            results.append({
                "source": url,
                "error": str(e)
            })

    return {
        "query": query,
        "results": results
    }


def enrich_portfolio_with_ai(portfolio):

    enriched = []

    for asset in portfolio:

        ticker = asset["asset"]

        news = get_market_news(ticker)
        sentiment_raw = analyze_sentiment(news)

        # ⚠️ ici simplification (tu peux parser plus tard)
        sentiment_score = 60  # temporaire

        trend_score = get_trends(ticker)

        price_change = 2  # temporaire (à connecter FMP)

        score = calculate_ai_score(
            sentiment_score,
            trend_score,
            price_change
        )

        enriched.append({
            **asset,
            "ai_score": score,
            "signal": get_signal(score),
            "risk": get_risk(score)
        })

    return enriched

def get_market(query="stock market"):

    insights = {
        "sentiment": "neutre",
        "trend": "stable",
        "news": []
    }

    try:
        # =========================
        # GOOGLE NEWS (gratuit)
        # =========================
        url = f"https://news.google.com/rss/search?q={query}"
        response = requests.get(url)

        if response.status_code == 200:
            insights["news"].append("Actualités récupérées depuis Google News")

    except:
        pass

    # =========================
    # LOGIQUE SIMPLE SENTIMENT
    # =========================
    if "crash" in query.lower():
        insights["sentiment"] = "bearish"
        insights["trend"] = "downtrend"
    elif "bull" in query.lower():
        insights["sentiment"] = "bullish"
        insights["trend"] = "uptrend"

    return insights
