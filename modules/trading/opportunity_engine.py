# =========================
# OPPORTUNITY ENGINE TRADING
# =========================
def get_trading_opportunities(user_profile):

    risk = user_profile.get("risk_profile", "medium")

    opportunities = []

    if risk == "low":

        opportunities.append({
            "title": "ETF long terme",
            "risk": "low",
            "potential": "medium",
            "type": "trading"
        })

    elif risk == "medium":

        opportunities.append({
            "title": "Swing trading actions",
            "risk": "medium",
            "potential": "high",
            "type": "trading"
        })

    else:

        opportunities.append({
            "title": "Trading crypto volatilité",
            "risk": "high",
            "potential": "high",
            "type": "trading"
        })

    return opportunities
