# =========================
# SCORING CONTEXT BUILDER
# =========================

from intelligence.analyzers.financial_overview import get_user_financial_overview


def build_scoring_context(user_profile: dict, portfolio: list, financial: dict = None):
    """
    Centralise toutes les données nécessaires au scoring modules.
    """

    financial = financial or {}

    # =========================
    # BASE CONTEXT
    # =========================
    context = {
        "profile": user_profile,
        "portfolio": portfolio,
        "financial": financial,

        # flatten important fields (compat legacy scorings)
        "capital": user_profile.get("capital", 0),
        "savings": user_profile.get("savings", 0),
        "risk_profile": user_profile.get("risk_profile", "medium"),
        "monthly_income": user_profile.get("monthly_income", 0),
        "experience": user_profile.get("experience", "low"),

        # AI / business signals
        "entrepreneurship_level": user_profile.get("entrepreneurship_level", 0),
        "startup_interest": user_profile.get("startup_interest", False),
        "networking": user_profile.get("networking", False),

        # crypto
        "crypto_experience": user_profile.get("crypto_experience", 0),

        # ai business
        "ai_interest": user_profile.get("ai_interest", False),
        "business_experience": user_profile.get("business_experience", 0),

        # computed financial overview (IMPORTANT)
        "financial_overview": get_user_financial_overview(user_profile.get("id"))
    }

    return context
