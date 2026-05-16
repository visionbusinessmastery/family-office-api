# =========================
# DIVERSIFICATION ENGINE
# =========================

def compute_diversification(context: dict):

    portfolio = context.get(
        "portfolio",
        []
    )

    asset_types = set()

    for asset in portfolio:

        asset_type = (
            asset.get("type", "")
            .lower()
        )

        if asset_type:
            asset_types.add(asset_type)

    diversification_score = min(
        len(asset_types) * 20,
        100
    )

    return {
        "diversification_score":
            diversification_score,

        "asset_classes":
            list(asset_types)
    }
