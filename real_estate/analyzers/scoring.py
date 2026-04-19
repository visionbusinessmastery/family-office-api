def score_property(property, yield_value, strategy):

    score = 0

    if yield_value > 8:
        score += 40
    elif yield_value > 5:
        score += 20

    surface = property.get("surface") or 0
    price = property.get("price") or 0
    market_price_m2 = property.get("market_price_m2")

    if surface <= 0:
        return score

    price_m2_property = price / surface

    if price_m2_property < 2000:
        score += 30

    if market_price_m2 and price_m2_property < market_price_m2:
        score += 20

    if strategy == "flip" and price_m2_property < 1500:
        score += 30

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
