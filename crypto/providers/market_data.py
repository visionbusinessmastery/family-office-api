def get_crypto_price(symbol: str):

    fake_market = {
        "BTC": 65000,
        "ETH": 3200,
        "SOL": 140
    }

    return {
        "symbol": symbol.upper(),
        "price": fake_market.get(symbol.upper(), 100)
    }
