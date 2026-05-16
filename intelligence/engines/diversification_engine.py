# =========================
# DIVERSIFICATION ENGINE (PRO VERSION)
# =========================

def compute_diversification(context: dict):

    portfolio = context.get("portfolio", []) or []

    asset_types = set()

    type_values = {}

    total_value = 0

    # =========================
    # SAFE ANALYSIS
    # =========================
    for asset in portfolio:

        if not isinstance(asset, dict):
            continue

        asset_type = (asset.get("type") or "").lower()
        value = float(asset.get("value") or 0)

        if not asset_type:
            continue

        asset_types.add(asset_type)

        type_values[asset_type] = type_values.get(asset_type, 0) + value
        total_value += value

    # =========================
    # TYPE COUNT SCORE (BASIC DIVERSIFICATION)
    # =========================
    type_score = min(len(asset_types) * 15, 60)

    # =========================
    # VALUE DISTRIBUTION SCORE
    # =========================
    concentration_penalty = 0

    if total_value > 0:

        for v in type_values.values():

            ratio = v / total_value

            # trop concentré sur un type
            if ratio > 0.6:
                concentration_penalty += 20
            elif ratio > 0.4:
                concentration_penalty += 10

    # =========================
    # FINAL SCORE
    # =========================
    diversification_score = type_score - concentration_penalty

    diversification_score = max(0, min(diversification_score, 100))

    # =========================
    # RESULT
    # =========================
    return {
        "diversification_score": diversification_score,
        "asset_classes": list(asset_types),
        "type_distribution": type_values,
        "total_value": total_value
    }
