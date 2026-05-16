import requests
import os
from openai import OpenAI

from market.sentiment import analyze_sentiment
from market.trends import get_trends
from market.scoring import calculate_ai_score, get_signal, get_risk

from data_engine.news_service import get_market_news, get_google_news


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# MARKET INTELLIGENCE V2
# =========================
def get_market_intelligence(query: str):

    news_fmp = get_market_news(query) or []
    news_google = get_google_news(query) or []

    # =========================
    # CLEAN MERGE + DEDUP
    # =========================
    all_news = {n.get("title", ""): n for n in (news_fmp + news_google)}
    news = list(all_news.values())

    sentiment = "neutral"
    sentiment_score = 50

    try:
        if news:
            sentiment_result = analyze_sentiment(news)

            # support dict or string safely
            if isinstance(sentiment_result, dict):
                sentiment = sentiment_result.get("label", "neutral")
                sentiment_score = sentiment_result.get("score", 50)
            else:
                sentiment = str(sentiment_result)

    except Exception:
        sentiment = "error"
        sentiment_score = 50

    return {
        "query": query,
        "news_count": len(news),
        "news": news[:5],
        "sentiment": sentiment,
        "sentiment_score": sentiment_score
    }
