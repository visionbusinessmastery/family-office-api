# =========================
# UNIFIED ORCHESTRATOR V4 FIX
# =========================

from sqlalchemy import text
from database import engine

from intelligence.analyzers.family_office_score import compute_family_office_score
from intelligence.analyzers.financial_overview import get_user_financial_overview

from intelligence.upgrade_engine import compute_upgrade_decision
from intelligence.feature_engine import compute_feature_access
from intelligence.dashboard_engine import build_dashboard

from intelligence.module_engine import get_all_opportunities

# ✅ AJOUT UNIQUE (SAFE)
from intelligence.gamification.orchestrator import build_gamification


# =========================
# CORE ORCHESTRATOR
# =========================
def run_orchestrator(user_email: str):

    with engine.begin() as conn:

        user = conn.execute(
            text("""
                SELECT id, email, plan, profile_completed
                FROM users
                WHERE email = :email
            """),
            {"email": user_email}
        ).fetchone()

        if not user:
            return {"error": "USER_NOT_FOUND"}

        if not user.profile_completed:
            return {
                "state": "ONBOARDING_REQUIRED",
                "score": {"score": 0},
                "level": "ONBOARDING"
            }

        profile = conn.execute(
            text("""
                SELECT *
                FROM user_profiles
                WHERE user_email = :email
            """),
            {"email": user_email}
        ).fetchone()

        profile_dict = dict(profile._mapping) if profile else {}

        portfolio_rows = conn.execute(
            text("""
                SELECT asset_name, category, quantity, purchase_price
                FROM portfolio
                WHERE user_id = :user_id
            """),
            {"user_id": user.id}
        ).fetchall()

        portfolio = []

        for p in portfolio_rows:
            qty = float(p.quantity or 0)
            price = float(p.purchase_price or 0)

            portfolio.append({
                "asset_name": p.asset_name,
                "type": (p.category or "").lower(),
                "value": qty * price
            })

        financial = get_user_financial_overview(user.id) or {}

        # =========================
        # SCORE ENGINE
        # =========================
        score_data = compute_family_office_score(
            profile_dict,
            portfolio,
            financial
        )

        score = score_data.get("score", 0)

        # =========================
        # MODULE OPPORTUNITIES
        # =========================
        user_profile = {
            **profile_dict,
            "portfolio": portfolio,
            "financial": financial,
            "score": score
        }

        opportunities = get_all_opportunities(user_profile)

        # =========================
        # UPGRADE ENGINE
        # =========================
        upgrade = compute_upgrade_decision(
            user.plan,
            score
        )

        # =========================
        # FEATURE ACCESS
        # =========================
        features = compute_feature_access(
            profile_dict,
            score_data
        )

        # =========================
        # DASHBOARD
        # =========================
        dashboard = build_dashboard(
            {"plan": user.plan},
            {
                "score": score_data,
                "level": upgrade.get("recommended_plan", "FREE")
            }
        )

        # =========================
        # 🧠 GAMIFICATION (AJOUT SAFE)
        # =========================
        streak = profile_dict.get("streak", 0) if isinstance(profile_dict, dict) else 0

        gamification = build_gamification(
            user,
            score,
            user.plan,
            streak
        )

        # =========================
        # FINAL RESPONSE
        # =========================
        return {
            "user": user.email,
            "plan": user.plan,

            "score": score_data,
            "upgrade": upgrade,
            "features": features,
            "opportunities": opportunities,
            "dashboard": dashboard,

            # 🔥 AJOUT SAFE
            "gamification": gamification,

            "portfolio_size": len(portfolio)
        }


# =========================
# COMPATIBILITY LAYER
# =========================
orchestrator = run_orchestrator
