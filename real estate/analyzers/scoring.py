def score_property(property, yield_value, strategy):

    score = 0

    # rendement
    if yield_value > 8:
        score += 40
    elif yield_value > 5:
        score += 20

    # prix au m²
    price_m2 = property["price"] / property["surface"]

    if price_m2 < 2000:
        score += 30

    # stratégie
    if strategy == "flip" and price_m2 < 1500:
        score += 30

    return score
