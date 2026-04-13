def score_crypto(trend: str, strategy: str):

    score = 0

    if trend == "bullish":
        score += 50

    if strategy == "long_term":
        score += 30

    if strategy == "trade":
        score += 20

    return score

def global_score(return_rate, risk, duration):
    score = 0

    score += return_rate * 2

    if risk == "low":
        score += 20
    elif risk == "medium":
        score += 10

    if duration < 24:
        score += 10

    return min(score, 100)
