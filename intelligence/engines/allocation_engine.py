# =========================
# AI ALLOCATION ENGINE (PRO)
# =========================

def compute_allocation_strategy(context: dict):

    profile = context.get("profile", {}) or {}
    portfolio = context.get("portfolio", []) or []

    risk = (
        profile.get("risk_profile", "medium")
        .lower()
    )

    savings = float(
        profile.get("epargne", 0)
        or 0
    )

    investments = float(
        profile.get("investments", 0)
        or 0
    )

    total_capital = savings + investments

    # =========================
    # CRYPTO EXPOSURE
    # =========================
    crypto_value = 0
    total_value = 0

    for asset in portfolio:

        if not isinstance(asset, dict):
            continue

        value = float(asset.get("value") or 0)
        total_value += value

        if (asset.get("type") or "").lower() == "crypto":
            crypto_value += value

    crypto_ratio = (
        crypto_value / total_value
        if total_value > 0
        else 0
    )

    # =========================
    # LOW RISK
    # =========================
    if risk == "low":

        allocation = {
            "cash": 35,
            "bonds": 35,
            "etf": 20,
            "crypto": 5,
            "stocks": 5,
        }

    # =========================
    # HIGH RISK
    # =========================
    elif risk == "high":

        allocation = {
            "stocks": 35,
            "crypto": 25,
            "private_equity": 20,
            "etf": 10,
            "cash": 10,
        }

    # =========================
    # MEDIUM RISK
    # =========================
    else:

        allocation = {
            "stocks": 30,
            "etf": 30,
            "real_estate": 20,
            "crypto": 10,
            "cash": 10,
        }

    # =========================
    # LARGE CAPITAL ADJUSTMENT
    # =========================
    if total_capital > 250000:

        allocation["private_equity"] = (
            allocation.get("private_equity", 0) + 10
        )

        allocation["cash"] = max(
            allocation.get("cash", 0) - 5,
            5
        )

    # =========================
    # CRYPTO OVEREXPOSURE SAFETY
    # =========================
    if crypto_ratio > 0.5:

        allocation["crypto"] = max(
            allocation.get("crypto", 0) - 10,
            5
        )

        allocation["cash"] = (
            allocation.get("cash", 0) + 5
        )

        allocation["etf"] = (
            allocation.get("etf", 0) + 5
        )

    # =========================
    # NORMALIZATION
    # =========================
    total_alloc = sum(allocation.values())

    if total_alloc != 100:

        factor = 100 / total_alloc

        allocation = {
            k: round(v * factor, 1)
            for k, v in allocation.items()
        }

    # =========================
    # RESULT
    # =========================
    return {
        "risk_profile": risk,
        "recommended_allocation": allocation,
        "crypto_exposure": round(
            crypto_ratio * 100,
            2
        ),
        "capital": round(total_capital, 2)
    }
