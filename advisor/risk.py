def compute_risk_metrics(portfolio):

    assets = portfolio.get("assets", [])
    total_value = sum(a.get("value", 0) for a in assets)

    # fake volatility estimation
    volatility = min(len(assets) * 5, 100)

    # drawdown simplifié
    drawdown = 0
    if total_value < 1000:
        drawdown = 20

    return {
        "volatility": volatility,
        "drawdown": drawdown,
        "risk_level": (
            "high" if volatility > 60 else
            "medium" if volatility > 30 else
            "low"
        )
    }
