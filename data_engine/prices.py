from stocks.service import resolve_ticker
from stocks.service import get_stock_data


def get_price(asset: str):

    ticker = resolve_ticker(asset)
    data = get_stock_data(ticker)

    if not data:
        return None

    return {
        "ticker": ticker,
        "price": data.get("price"),
        "source": data.get("source", "unknown")
    }
