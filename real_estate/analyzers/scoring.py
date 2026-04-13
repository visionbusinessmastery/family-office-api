def score_property(property, yield_value, strategy):

    score = 0

    if yield_value > 8:
        score += 40
    elif yield_value > 5:
        score += 20

    price_m2 = property["price"] / property["surface"]
    price_m2_market = estimate_price_m2(query.city)
    price_m2_property = property["price"] / property["surface"]
        
    if price_m2 < 2000:
        score += 30

    if price_m2_property < price_m2_market:
       score += 20

    if strategy == "flip" and price_m2 < 1500:
        score += 30

    return score
