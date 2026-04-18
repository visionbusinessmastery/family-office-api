import requests
import json
import os
from market.service import get_market_news
from portfolio.service import get_user_portfolio


# =========================
# SIMPLE ALERT ENGINE
# =========================
def generate_alerts(user_email):

    portfolio = get_user_portfolio(user_email)
    data = json.loads(data)

    alerts = []

    for asset in portfolio:

        ticker = asset["asset"]
        quantity = asset["quantity"]
        gain_percent = asset["gain_percent"]

        # 🔥 ALERT 1 : forte perte
        if gain_percent < -10:
            alerts.append({
                "type": "CRITICAL",
                "asset": ticker,
                "message": f"{ticker} en forte baisse ({gain_percent}%)"
            })

        # 🔥 ALERT 2 : forte hausse
        if gain_percent > 15:
            alerts.append({
                "type": "OPPORTUNITY",
                "asset": ticker,
                "message": f"{ticker} forte performance (+{gain_percent}%)"
            })

        # 🔥 ALERT 3 : news impact (simple)
        news = get_market_news(ticker)

        if news:
            alerts.append({
                "type": "NEWS",
                "asset": ticker,
                "message": f"Actualité récente détectée sur {ticker}"
            })

    return {
        "alerts": alerts,
        "count": len(alerts)
    }
