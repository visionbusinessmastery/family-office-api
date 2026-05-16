# =========================
# AI WEALTH ENGINE (PREMIUM)
# =========================

def compute_wealth_projection(context: dict):

    profile = context.get("profile", {}) or {}

    # =========================
    # SAFE INPUTS
    # =========================
    monthly_income = float(
        profile.get("monthly_income", 0)
        or 0
    )

    savings = float(
        profile.get("epargne", 0)
        or 0
    )

    investments = float(
        profile.get("investments", 0)
        or 0
    )

    risk_profile = (
        profile.get("risk_profile", "medium")
        .lower()
    )

    # =========================
    # CURRENT WEALTH
    # =========================
    current_wealth = (
        savings + investments
    )

    # =========================
    # MONTHLY SAVING ESTIMATION
    # =========================
    monthly_saving_capacity = (
        monthly_income * 0.20
    )

    yearly_contribution = (
        monthly_saving_capacity * 12
    )

    # =========================
    # RETURN RATE
    # =========================
    if risk_profile == "low":
        annual_return = 0.04

    elif risk_profile == "high":
        annual_return = 0.12

    else:
        annual_return = 0.08

    # =========================
    # COMPOUND ENGINE
    # =========================
    def project(years):

        wealth = current_wealth

        for _ in range(years):

            wealth = (
                wealth * (1 + annual_return)
            ) + yearly_contribution

        return round(wealth, 2)

    projection_3y = project(3)
    projection_5y = project(5)
    projection_10y = project(10)

    # =========================
    # WEALTH LEVEL
    # =========================
    if projection_10y >= 5_000_000:
        wealth_level = "ULTRA_HIGH"

    elif projection_10y >= 1_000_000:
        wealth_level = "VERY_HIGH"

    elif projection_10y >= 500_000:
        wealth_level = "HIGH"

    elif projection_10y >= 150_000:
        wealth_level = "MEDIUM"

    else:
        wealth_level = "LOW"

    # =========================
    # WEALTH TRAJECTORY
    # =========================
    if projection_10y > current_wealth * 5:
        trajectory = "EXPONENTIAL"

    elif projection_10y > current_wealth * 2:
        trajectory = "STRONG_GROWTH"

    else:
        trajectory = "MODERATE"

    # =========================
    # RESULT
    # =========================
    return {

        "current_wealth":
            round(current_wealth, 2),

        "monthly_saving_capacity":
            round(monthly_saving_capacity, 2),

        "estimated_return_rate":
            round(annual_return * 100, 2),

        "3y_projection":
            projection_3y,

        "5y_projection":
            projection_5y,

        "10y_projection":
            projection_10y,

        "wealth_level":
            wealth_level,

        "trajectory":
            trajectory,
    }
