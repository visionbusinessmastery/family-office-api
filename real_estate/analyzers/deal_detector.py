def detect_deal(prop, market_price_m2):

    price_m2 = prop["price"] / prop["surface"]

    ratio = price_m2 / market_price_m2

    if ratio < 0.6:
        return "🔥 énorme opportunité"
    elif ratio < 0.8:
        return "✅ bonne affaire"
    elif ratio < 1:
        return "correct"
    else:
        return "cher"
