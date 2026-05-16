# =========================
# AI PREDICTION ENGINE (PRO)
# =========================

def compute_predictions(context: dict):

    profile = context.get("profile", {}) or {}
    financial = context.get("financial", {}) or {}

    # =========================
    # SAFE VALUES
    # =========================
    monthly_income = float(
        profile.get("monthly_income")
        or 0
    )

    savings = float(
        profile.get("epargne")
        or profile.get("savings")
        or 0
    )

    investments = float(
        profile.get("investments")
        or 0
    )

    risk_profile = (
        profile.get("risk_profile", "medium")
        .lower()
    )

    # =========================
    # SAVINGS RATE ESTIMATION
    # =========================
    estimated_monthly_saving = (
        monthly_income * 0.20
    )

    yearly_contribution = (
        estimated_monthly_saving * 12
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
    # INITIAL CAPITAL
    # =========================
    capital = savings + investments

    # =========================
    # COMPOUND PROJECTION
    # =========================
    def project(years):

        future = capital

        for _ in range(years):

            future = (
                future * (1 + annual_return)
            ) + yearly_contribution

        return round(future, 2)

    projection_3y = project(3)
    projection_5y = project(5)
    projection_10y = project(10)

    # =========================
    # FINANCIAL TRAJECTORY
    # =========================
    if projection_10y >= 1000000:
        trajectory = "WEALTH ACCELERATION"

    elif projection_10y >= 250000:
        trajectory = "STRONG GROWTH"

    elif projection_10y >= 100000:
        trajectory = "POSITIVE"

    else:
        trajectory = "STABLE"

    # =========================
    # ETA FINANCIAL FREEDOM
    # =========================
    if yearly_contribution > 0:

        freedom_target = 1000000

        years_to_freedom = int(
            max(
                (freedom_target - capital)
                / yearly_contribution,
                0
            )
        )

    else:
        years_to_freedom = None

    # =========================
    # RESULT
    # =========================
    return {

        "3y_projection": projection_3y,

        "5y_projection": projection_5y,

        "10y_projection": projection_10y,

        "financial_trajectory": trajectory,

        "estimated_return_rate": round(
            annual_return * 100,
            2
        ),

        "estimated_years_to_financial_freedom":
            years_to_freedom,
    }
