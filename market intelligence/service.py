import requests
from config import FMP_API_KEY
from openai import OpenAI

client = OpenAI()

def get_market_news(ticker):

    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={ticker}&limit=5&apikey={FMP_API_KEY}"
    
    try:
        res = requests.get(url)
        data = res.json()
        return data
    except:
        return []
