# =========================
# AI WEALTH ENGINE
# =========================

def compute_wealth_projection(context: dict):

    income = context.get("monthly_income", 0)
    savings = context.get("savings", 0)

    yearly_projection = (
        income * 12
    ) + savings

    five_year_projection = (
        yearly_projection * 5
    )

    return {

        "yearly_projection": yearly_projection,

        "five_year_projection": (
            five_year_projection
        ),

        "wealth_level": (
            "HIGH"
            if five_year_projection > 500000
            else "MEDIUM"
        )
    }
