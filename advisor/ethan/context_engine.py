def compact_context(context):
    score = context.get("global_score") or context.get("score") or 0
    if isinstance(score, dict):
        score = score.get("score", 0)

    data_profile = context.get("data_profile") or {}
    financial = context.get("financial_features") or {}
    opportunities = context.get("opportunities") or {}
    opportunity_count = (
        len(opportunities)
        if isinstance(opportunities, list)
        else opportunities.get("count", 0)
        if isinstance(opportunities, dict)
        else 0
    )

    return {
        "score": score,
        "level": context.get("level"),
        "plan": context.get("plan"),
        "status": context.get("state", "READY"),
        "life_context": context.get("life_context") or {},
        "opportunity_count": opportunity_count,
        "completion_percent": data_profile.get("completion_percent"),
        "cashflow": financial.get("cashflow_score"),
        "debt_risk": financial.get("debt_risk_score"),
        "savings_velocity": financial.get("savings_velocity_score"),
        "module_signals": (context.get("module_signals") or [])[:5],
    }


def compact_portfolio(portfolio):
    assets = portfolio.get("portfolio") if isinstance(portfolio, dict) else portfolio
    if not isinstance(assets, list):
        assets = portfolio.get("assets", []) if isinstance(portfolio, dict) else []

    total_value = 0
    exposures = {}
    top_assets = []

    for asset in assets[:80]:
        name = asset.get("asset_name") or asset.get("name") or "Asset"
        category = (asset.get("asset_type") or asset.get("category") or asset.get("type") or "OTHER").upper()
        value = float(asset.get("value") or asset.get("current_value") or 0)
        if not value:
            qty = float(asset.get("quantity") or 0)
            price = float(asset.get("current_price") or asset.get("purchase_price") or 0)
            value = qty * price

        total_value += value
        exposures[category] = exposures.get(category, 0) + value
        top_assets.append({"name": name, "category": category, "value": round(value, 2)})

    top_assets = sorted(top_assets, key=lambda item: item["value"], reverse=True)[:5]

    return {
        "asset_count": len(assets),
        "total_value": round(total_value, 2),
        "exposures": dict(sorted(exposures.items(), key=lambda item: item[1], reverse=True)[:6]),
        "top_assets": top_assets,
    }
