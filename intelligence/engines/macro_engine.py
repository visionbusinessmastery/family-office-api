# =========================
# MACRO ENGINE
# =========================

def compute_macro_exposure(context: dict):

    crypto_ratio = context.get(
        "crypto_ratio",
        0
    )

    if crypto_ratio > 0.4:

        macro = (
            "HIGH EXPOSURE TO VOLATILITY"
        )

    else:

        macro = (
            "BALANCED MACRO EXPOSURE"
        )

    return {
        "macro_outlook": macro
    }
