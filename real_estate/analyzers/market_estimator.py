def estimate_price_m2(city: str):

    # ⚠️ MVP simple (à améliorer plus tard avec vraie data)
    base_prices = {
        "paris": 10000,
        "marseille": 3500,
        "lyon": 5000,
        "toulouse": 4000
    }

    return base_prices.get(city.lower(), 3000)
