def score_opportunity(item, mode):
    score = 0

    # base quality signals
    score += min(item.get("market_size", 0) / 1000, 30)
    score += min(item.get("competition_level", 10) * -2 + 20, 20)

    if mode == "buy":
        score += 20
    elif mode == "grow":
        score += 15
    elif mode == "create":
        score += 10

    return min(score, 100)
