def normalize_portfolio(rows):

    merged = {}

    for r in rows:
        key = (r.asset, r.asset_type)

        if key not in merged:
            merged[key] = {
                "asset": r.asset,
                "asset_type": r.asset_type,
                "quantity": 0,
                "buy_price_total": 0,
                "count": 0
            }

        merged[key]["quantity"] += float(r.quantity or 0)
        merged[key]["buy_price_total"] += float(r.buy_price or 0)
        merged[key]["count"] += 1

    return list(merged.values())
