# =========================
# AI PREDICTION ENGINE
# =========================

def compute_predictions(context: dict):

    income = context.get(
        "monthly_income",
        0
    )

    savings = context.get(
        "savings",
        0
    )

    future_capital = (
        savings + (income * 12 * 3)
    )

    return {

        "3y_projection":
            future_capital,

        "prediction":
            "POSITIVE"
            if future_capital > 100000
            else "STABLE"
    }
