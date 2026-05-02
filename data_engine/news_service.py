import requests
import os
from openai import OpenAI
from market.sentiment import analyze_sentiment
from market.trends import get_trends
from market.scoring import calculate_ai_score, get_signal, get_risk
import xml.etree.ElementTree as ET  # 🔥 ajout


FMP_API_KEY = os.getenv("FMP_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# NEWS FMP (AMÉLIORÉ SAFE)
# =========================
def get_market_news(ticker):

    if not FMP_API_KEY:
        return []

    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={ticker}&limit=5&apikey={FMP_API_KEY}"
    
    try:
        res = requests.get(url, timeout=5)

        if res.status_code != 200:
            return []

        data = res.json()

        # 🔥 normalisation
        return [
            {
                "title": item.get("title"),
                "source": item.get("site"),
                "url": item.get("url")
            }
            for item in data
        ]

    except Exception:
        return []


# =========================
# 🔥 GOOGLE NEWS RSS (NOUVEAU)
# =========================
def get_google_news(query):

    url = f"https://news.google.com/rss/search?q={query}"

    articles = []

    try:
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            return []

        root = ET.fromstring(response.content)

        for item in root.findall(".//item")[:5]:
            articles.append({
                "title": item.find("title").text if item.find("title") is not None else "",
                "link": item.find("link").text if item.find("link") is not None else "",
                "source": "Google News"
            })

    except Exception:
        return []
