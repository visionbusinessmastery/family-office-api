import requests
from config import FMP_API_KEY
from openai import OpenAI
from market_intelligence.service import get_market_news
from market_intelligence.sentiment import analyze_sentiment
from market_intelligence.trends import get_trends

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_market_news(ticker):

    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={ticker}&limit=5&apikey={FMP_API_KEY}"
    
    try:
        res = requests.get(url)
        data = res.json()
        return data
    except:
        return []


def enrich_portfolio_with_ai(portfolio):

    enriched = []

    for asset in portfolio:

        ticker = asset["asset"]

        news = get_market_news(ticker)
        sentiment = analyze_sentiment(news)
        trend_score = get_trends(ticker)

        enriched.append({
            **asset,
            "sentiment": sentiment,
            "trend_score": trend_score
        })

    return enriched
