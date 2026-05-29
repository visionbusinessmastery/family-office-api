def analyze_sentiment(news_list):
    titles = " ".join(str(article.get("title", "")) for article in news_list or []).lower()
    bearish_terms = ["crash", "baisse", "bearish", "recession", "fear", "selloff", "chute", "risk"]
    bullish_terms = ["bull", "hausse", "record", "rally", "growth", "croissance", "optimism", "gain"]

    bearish_count = sum(1 for term in bearish_terms if term in titles)
    bullish_count = sum(1 for term in bullish_terms if term in titles)

    if bullish_count > bearish_count:
        label = "bullish"
        score = min(75, 55 + bullish_count * 5)
    elif bearish_count > bullish_count:
        label = "bearish"
        score = max(25, 45 - bearish_count * 5)
    else:
        label = "neutral"
        score = 50

    return {
        "label": label,
        "score": score,
        "summary": "Signal marche calcule localement. Interpretation strategique reservee au moteur central.",
    }
