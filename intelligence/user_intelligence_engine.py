# =========================
# IMPORTS
# =========================
from sqlalchemy import text
from database import engine

from intelligence.analyzers.family_office_score import compute_family_office_score
from intelligence.upgrade_engine import compute_upgrade_decision
from intelligence.feature_engine import compute_feature_access
from intelligence.opportunity_engine import compute_opportunities

from intelligence.analyzers.financial_overview import get_user_financial_overview


# =========================
# PUBLIC CORE API
# =========================
def get_user_intelligence(user_email: str):
    return compute_user_intelligence(user_email)


# =========================
# SAFE HELPERS
# =========================
def safe_get(obj, key, default=0):
    try:
        return obj.get(key, default) if isinstance(obj, dict) else default
    except:
        return default


# =========================
# MAIN ENGINE
# =========================
def compute_user_intelligence(user_email: str):

    with engine.begin() as conn:

        # =========================
        # 1. USER
        # =========================
        user = conn.execute(text("""
            SELECT id, email, plan, profile_completed
            FROM users
            WHERE email = :email
        """), {"email": user_email}).fetchone()

        if not user:
            return {"error": "user not found"}

        if not user.profile_completed:
            return {
                "state": "ONBOARDING_REQUIRED",
                "score": {"score": 0},
                "level": "ONBOARDING",
                "features": [],
                "opportunities": [],
                "upgrade": None
            }

        # =========================
        # 2. PROFILE
        # =========================
        profile = conn.execute(text("""
            SELECT *
            FROM user_profiles
            WHERE user_email = :email
        """), {"email": user_email}).fetchone()

        profile_dict = dict(profile._mapping) if profile else {}

        # =========================
        # 2.1 ONBOARDING DATA (NEW)
        # =========================
        onboarding_data = conn.execute(text("""
            SELECT revenus_mensuels, dettes, epargne
            FROM users
            WHERE email = :email
        """), {"email": user_email}).fetchone()

        onboarding = {
            "revenus": float(onboarding_data.revenus_mensuels or 0) if onboarding_data else 0,
            "dettes": float(onboarding_data.dettes or 0) if onboarding_data else 0,
            "epargne": float(onboarding_data.epargne or 0) if onboarding_data else 0,
        }

        # =========================
        # 🔥 MERGE PROFILE + ONBOARDING
        # =========================
        profile_dict = {
            # 💰 capital (épargne onboarding fallback)
            "savings": float(
                profile_dict.get("savings")
                or onboarding.get("epargne")
                or 0
            ),

            # 📈 investissements
            "investments": float(profile_dict.get("investments") or 0),

            # ⚖️ risque
            "risk_profile": (
                profile_dict.get("risk_profile")
                or "medium"
            ).lower(),

            # 🔥 NEW DATA (utile pour futur)
            "monthly_income": float(onboarding.get("revenus_mensuels") or 0),
            "debt": float(onboarding.get("dettes") or 0),
        }

        profile_dict["email"] = user.email
        profile_dict["plan"] = user.plan

        # =========================
        # 3. PORTFOLIO
        # =========================
        portfolio = conn.execute(text("""
            SELECT asset_name, category, quantity, purchase_price
            FROM portfolio
            WHERE user_id = :user_id
        """), {"user_id": user.id}).fetchall()

        portfolio_list = []

        for p in portfolio:
            qty = float(p.quantity or 0)
            price = float(p.purchase_price or 0)

            portfolio_list.append({
                "asset_name": p.asset_name,
                "type": (p.category or "").lower(),
                "value": qty * price
            })

        # 🔥 FIX : fallback investments depuis portfolio
        if profile_dict["investments"] == 0 and portfolio_list:
            profile_dict["investments"] = sum(
                [a.get("value", 0) for a in portfolio_list]
            )

        # =========================
        # 4. FINANCIAL DATA (SAFE)
        # =========================
        financial = get_user_financial_overview(user.id) or {}

        financial_features = None
        totals = financial.get("totals", {})

        if totals:

            income = safe_get(totals, "monthly_income", 0)
            debt = safe_get(totals, "total_debt", 0)
            savings = safe_get(totals, "total_savings", 0)
            cashflow = safe_get(totals, "net_cashflow", 0)

            cashflow_score = (cashflow / (income + 1)) * 100
            cashflow_score = max(min(cashflow_score, 100), -100)

            debt_risk_score = min((debt / (savings + 1)) * 100, 100)
            savings_velocity = (savings / (income + 1)) * 100

            income_sources = financial.get("income_sources", [])
            income_stability_score = min(len(income_sources) * 25, 100)

            financial_features = {
                "cashflow_score": round(cashflow_score, 2),
                "debt_risk_score": round(debt_risk_score, 2),
                "savings_velocity_score": round(savings_velocity, 2),
                "income_stability_score": round(income_stability_score, 2),
                "raw": totals
            }

        # =========================
        # 5. FAMILY OFFICE SCORE
        # =========================
        score_result = compute_family_office_score(
            profile_dict,
            portfolio_list,
            financial_features
        ) or {}

        # =========================
        # SAFE SCORE EXTRACTION
        # =========================
        score = safe_get(score_result, "score", 0)

        if isinstance(score, dict):
            score = safe_get(score, "score", 0)

        score = int(score or 0)

        # =========================
        # 6. LEVEL
        # =========================
        if score >= 80:
            level = "ELITE"
        elif score >= 60:
            level = "GOLD"
        elif score >= 40:
            level = "SILVER"
        else:
            level = "FREE"

        # =========================
        # 7. AI ENGINE
        # =========================
        upgrade = compute_upgrade_decision(user.plan, score)
        features = compute_feature_access(profile_dict, score_result)
        opportunities = compute_opportunities(profile_dict, portfolio_list)

        return {
            "user": user.email,
            "plan": user.plan,
            "score": {
                "score": score,
                "details": score_result.get("details", {}),
                "advice": score_result.get("advice", [])
            },
            "level": level,
            "onboarding": onboarding_dict,
            "upgrade": upgrade,
            "features": features,
            "opportunities": opportunities
        }
