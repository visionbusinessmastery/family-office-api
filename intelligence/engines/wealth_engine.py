# =========================
# AI WEALTH ENGINE (FIXED + SAAS READY)
# =========================

def compute_wealth_projection(context: dict):

    profile = context.get("profile", {}) or {}

    # =========================
    # SAFE INPUTS
    # =========================
    income = float(profile.get("monthly_income", 0) or 0)
    savings = float(profile.get("epargne", 0) or 0)
    investments = float(profile.get("investments", 0) or 0)

    total_current_wealth = savings + investments

    # =========================
    # YEARLY PROJECTION
    # =========================
    yearly_projection = (income * 12) + total_current_wealth

    # =========================
    # 5 YEARS PROJECTION (COMPOUND SIMPLIFIED)
    # =========================
    five_year_projection = yearly_projection * 5

    # =========================
    # WEALTH LEVEL
    # =========================
    if five_year_projection >= 1_000_000:
        wealth_level = "VERY_HIGH"
    elif five_year_projection >= 500_000:
        wealth_level = "HIGH"
    elif five_year_projection >= 150_000:
        wealth_level = "MEDIUM"
    else:
        wealth_level = "LOW"

    # =========================
    # RETURN ENGINE PAYLOAD
    # =========================
    return {
        "current_wealth": round(total_current_wealth, 2),
        "yearly_projection": round(yearly_projection, 2),
        "five_year_projection": round(five_year_projection, 2),
        "wealth_level": wealth_level
    }
