def score_crypto(trend: str, strategy: str):

    score = 0

    if trend == "bullish":
        score += 50

    if strategy == "long_term":
        score += 30

    if strategy == "trade":
        score += 20

    return score
