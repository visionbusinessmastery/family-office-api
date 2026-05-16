# =========================
# MACRO ENGINE (FIXED + REAL DATA)
# =========================

def compute_macro_exposure(context: dict):

    portfolio = context.get("portfolio", []) or []

    total_value = 0
    crypto_value = 0

    # =========================
    # PORTFOLIO ANALYSIS
    # =========================
    for asset in portfolio:

        if not isinstance(asset, dict):
            continue

        value = float(asset.get("value", 0) or 0)
        asset_type = (asset.get("type") or "").lower()

        total_value += value

        if asset_type == "crypto":
            crypto_value += value

    crypto_ratio = (crypto_value / total_value) if total_value > 0 else 0

    # =========================
    # MACRO LOGIC
    # =========================
    if crypto_ratio > 0.5:
        macro = "EXTREME VOLATILITY EXPOSURE"
        regime = "RISKY"

    elif crypto_ratio > 0.3:
        macro = "HIGH VOLATILITY EXPOSURE"
        regime = "MODERATE-RISK"

    elif crypto_ratio > 0.1:
        macro = "BALANCED EXPOSURE"
        regime = "STABLE"

    else:
        macro = "CONSERVATIVE ALLOCATION"
        regime = "LOW-RISK"

    # =========================
    # FUTURE EXTENSION READY
    # =========================
    return {
        "macro_outlook": macro,
        "risk_regime": regime,
        "crypto_ratio": round(crypto_ratio, 3),
        "portfolio_exposure": round(total_value, 2)
    }
