# =========================
# IMPORTS
# =========================
from sqlalchemy import text
from database import engine

from intelligence.core.upgrade_engine import (
    compute_upgrade_decision
)

from intelligence.strategic.feature_engine import (
    compute_feature_access
)

from intelligence.strategic.opportunity_engine import (
    compute_opportunities
)

from intelligence.strategic.strategic_layer import (
    compute_strategic_layer
)

from intelligence.scoring.financial_overview import (
    get_user_financial_overview
)

from intelligence.scoring.family_office_score import (
    compute_family_office_score
)


# =========================
# SAFE GETTER
# =========================
def safe_get(obj, key, default=0):

    try:
        return obj.get(key, default) if isinstance(obj, dict) else default

    except Exception:
        return default


# =========================
# LEVEL SYSTEM (UNIFIED)
# =========================
def compute_level(
    score_value: int,
    plan: str = "FREE"
):

    plan = (plan or "FREE").upper()

    # PREMIUM OVERRIDE
    if plan == "LIBERTY":
        return "LIBERTY"

    # SCORE LEVELS
    if score_value >= 15000:
        return "LIBERTY"

    elif score_value >= 7000:
        return "ELITE"

    elif score_value >= 3000:
        return "ELITE"

    elif score_value >= 1000:
        return "GOLD"

    elif score_value >= 80:
        return "ELITE"

    elif score_value >= 60:
        return "GOLD"

    elif score_value >= 40:
        return "SILVER"

    else:
        return "FREE"


# =========================
# PUBLIC API
# =========================
def get_user_intelligence(user_email: str):

    return compute_user_intelligence(
        user_email
    )


# =========================
# MAIN ENGINE
# =========================
def compute_user_intelligence(
    user_email: str
):

    with engine.begin() as conn:

        # =========================
        # USER FETCH
        # =========================
        user = conn.execute(text("""
            SELECT
                id,
                email,
                plan,
                profile_completed
            FROM users
            WHERE email = :email
        """), {
            "email": user_email
        }).fetchone()

        if not user:

            return {
                "error": "user not found"
            }

        profile_completed = getattr(
            user,
            "profile_completed",
            False
        )

        # =========================
        # ONBOARDING REQUIRED
        # =========================
        if not profile_completed:

            return {
                "state": "ONBOARDING_REQUIRED",
                "score": {
                    "score": 0
                },
                "level": "ONBOARDING",
                "features": [],
                "opportunities": [],
                "upgrade": None
            }

        # =========================
        # PROFILE FETCH
        # =========================
        profile = conn.execute(text("""
            SELECT *
            FROM user_profiles
            WHERE user_email = :email
        """), {
            "email": user_email
        }).fetchone()

        profile_dict = (
            dict(profile._mapping)
            if profile
            else {}
        )

        # =========================
        # ONBOARDING DATA
        # =========================
        onboarding_data = conn.execute(text("""
            SELECT
                revenus_mensuels,
                charges_mensuelles
            FROM users
            WHERE email = :email
        """), {
            "email": user_email
        }).fetchone()

        onboarding = {

            "revenus_mensuels": float(
                getattr(
                    onboarding_data,
                    "revenus_mensuels",
                    0
                ) or 0
            ),

            "charges_mensuelles": float(
                getattr(
                    onboarding_data,
                    "charges_mensuelles",
                    0
                ) or 0
            ),

            "epargne": float(
                profile_dict.get("savings") or 0
            ),

            "dettes": float(
                profile_dict.get("debts") or 0
            ),
        }

        # =========================
        # PROFILE SAFE MERGE
        # =========================
        profile_dict = {

            "epargne": float(
                profile_dict.get("epargne")
                or onboarding["epargne"]
                or 0
            ),

            "investments": float(
                profile_dict.get("investments")
                or 0
            ),

            "risk_profile": (
                profile_dict.get("risk_profile")
                or "medium"
            ).lower(),

            "monthly_income": float(
                onboarding["revenus_mensuels"]
                or 0
            ),

            "debt": float(
                onboarding["dettes"]
                or 0
            ),
        }

        profile_dict["email"] = user.email
        profile_dict["plan"] = user.plan

        # =========================
        # PORTFOLIO
        # =========================
        rows = conn.execute(text("""
            SELECT
                asset_name,
                category,
                quantity,
                purchase_price
            FROM portfolio
            WHERE user_id = :user_id
        """), {
            "user_id": user.id
        }).fetchall()

        portfolio_list = []

        for p in rows:

            qty = float(
                getattr(p, "quantity", 0) or 0
            )

            price = float(
                getattr(
                    p,
                    "purchase_price",
                    0
                ) or 0
            )

            portfolio_list.append({

                "asset_name": getattr(
                    p,
                    "asset_name",
                    ""
                ),

                "type": (
                    getattr(
                        p,
                        "category",
                        ""
                    ) or ""
                ).lower(),

                "value": qty * price
            })

        # =========================
        # FALLBACK INVESTMENTS
        # =========================
        if (
            profile_dict["investments"] == 0
            and portfolio_list
        ):

            profile_dict["investments"] = sum(
                x["value"]
                for x in portfolio_list
            )

        # =========================
        # FINANCIAL OVERVIEW
        # =========================
        financial = (
            get_user_financial_overview(
                user.id
            ) or {}
        )

        financial_features = None

        totals = financial.get(
            "totals",
            {}
        ) if isinstance(
            financial,
            dict
        ) else {}

        if totals:

            income = safe_get(
                totals,
                "monthly_income",
                0
            )

            debt = safe_get(
                totals,
                "total_debt",
                0
            )

            savings = safe_get(
                totals,
                "total_savings",
                0
            )

            cashflow = safe_get(
                totals,
                "net_cashflow",
                0
            )

            cashflow_score = (
                (cashflow / (income + 1)) * 100
            )

            cashflow_score = max(
                min(cashflow_score, 100),
                -100
            )

            debt_risk_score = min(
                (
                    debt / (savings + 1)
                ) * 100,
                100
            )

            savings_velocity = (
                savings / (income + 1)
            ) * 100

            income_sources = financial.get(
                "income_sources",
                []
            )

            income_stability_score = min(
                len(income_sources) * 25,
                100
            )

            financial_features = {

                "cashflow_score": round(
                    cashflow_score,
                    2
                ),

                "debt_risk_score": round(
                    debt_risk_score,
                    2
                ),

                "savings_velocity_score": round(
                    savings_velocity,
                    2
                ),

                "income_stability_score": round(
                    income_stability_score,
                    2
                ),

                "raw": totals
            }

        # =========================
        # SCORE ENGINE
        # =========================
        score_result = (
            compute_family_office_score(
                profile_dict,
                portfolio_list,
                financial_features
            ) or {}
        )

        score_value = safe_get(
            score_result,
            "score",
            0
        )

        if isinstance(score_value, dict):

            score_value = safe_get(
                score_value,
                "score",
                0
            )

        score_value = int(
            score_value or 0
        )

        # =========================
        # LEVEL
        # =========================
        level = compute_level(
            score_value,
            user.plan
        )

        # =========================
        # AI MODULES
        # =========================
        upgrade = compute_upgrade_decision(
            user.plan,
            score_value
        )

        features = compute_feature_access(
            profile_dict,
            score_result
        )

        opportunities = compute_opportunities(
            profile_dict,
            portfolio_list
        )

        # =========================
        # STRATEGIC CONTEXT
        # =========================
        context = {
            "profile": profile_dict,
            "portfolio": portfolio_list,
            "financial": financial_features,
            "score": score_result
        }

        modules = {
            "upgrade": upgrade,
            "features": features,
            "opportunities": opportunities
        }

        # =========================
        # STRATEGIC LAYER
        # =========================
        strategic_intelligence = (
            compute_strategic_layer(
                context,
                modules
            )
        )

        # =========================
        # FINAL RESPONSE
        # =========================
        return {

            "user": user.email,

            "plan": user.plan,

            "strategic_intelligence": (
                strategic_intelligence
            ),

            "score": {

                "score": score_value,

                "details": score_result.get(
                    "details",
                    {}
                ),

                "advice": score_result.get(
                    "advice",
                    []
                )
            },

            "level": level,

            "onboarding": onboarding,

            "upgrade": upgrade,

            "features": features,

            "opportunities": opportunities
        }
