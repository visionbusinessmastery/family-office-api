import requests
import os
from openai import OpenAI
from market.sentiment import analyze_sentiment
from market.trends import get_trends
from market.scoring import calculate_ai_score, get_signal, get_risk
import xml.etree.ElementTree as ET  # 🔥 ajout
from data_engine.news_service import get_market_news, get_google_news


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# 🔥 MARKET INTELLIGENCE (FIX)
# =========================
def get_market_intelligence(query: str):
    """
    Version PRO sans scraping
    """

    # 1️⃣ NEWS FMP
    news_fmp = get_market_news(query)

    # 2️⃣ NEWS GOOGLE
    news_google = get_google_news(query)

    # 🔥 fusion
    news = news_fmp + news_google

    # 3️⃣ SENTIMENT IA
    sentiment = None

    try:
        if news:
            sentiment = analyze_sentiment(news)
    except Exception:
        sentiment = "Analyse indisponible"

    return {
        "query": query,
        "news_count": len(news),
        "news": news[:5],  # limiter propre
        "sentiment": sentiment
    }


# =========================
# ENRICH PORTFOLIO (inchangé)
# =========================
def enrich_portfolio_with_ai(portfolio):

    enriched = []

    for asset in portfolio:

        ticker = asset["asset"]

        news = get_market_news(ticker)
        analyze_sentiment(news)

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


# =========================
# MARKET SIMPLE (légèrement amélioré)
# =========================
def get_market(query="stock market"):

    insights = {
        "sentiment": "neutre",
        "trend": "stable",
        "news": []
    }

    try:
        news = get_google_news(query)

        if news:
            insights["news"] = [n["title"] for n in news]

    except Exception:
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
