def allocate_portfolio(query, real, crypto, stocks):

    if query.risk == "low":
        return {
            "real_estate": 60,
            "stocks": 30,
            "crypto": 10
        }

    elif query.risk == "medium":
        return {
            "real_estate": 40,
            "stocks": 40,
            "crypto": 20
        }

    else:
        return {
            "real_estate": 20,
            "stocks": 40,
            "crypto": 40
        }
