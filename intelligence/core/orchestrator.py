# =========================
# UNIFIED ORCHESTRATOR V4 (FIXED + SAAS READY)
# =========================

import json
import hashlib

from sqlalchemy import text
from database import engine

from core.cache import redis_client

from intelligence.scoring.family_office_score import compute_family_office_score
from intelligence.scoring.financial_overview import get_user_financial_overview

from intelligence.core.upgrade_engine import compute_upgrade_decision
from intelligence.strategic.feature_engine import compute_feature_access
from intelligence.strategic.dashboard_engine import build_dashboard
from intelligence.strategic.module_engine import get_all_opportunities

from intelligence.gamification.core.gamification_engine import build_gamification


# =========================
# CACHE HELPERS
# =========================
def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except:
        pass
    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


# =========================
# HASH BUILDER (ORCHESTRATOR CACHE)
# =========================
def build_hash(user_email):

    return hashlib.md5(
        user_email.encode()
    ).hexdigest()


# =========================
# CORE ORCHESTRATOR
# =========================
def run_orchestrator(user_email: str):

    cache_key = f"orchestrator:{build_hash(user_email)}"

    # =========================
    # CACHE CHECK
    # =========================
    cached = get_cache(cache_key)
    if cached:
        return cached

    with engine.begin() as conn:

        # =========================
        # USER FETCH
        # =========================
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

        # =========================
        # ONBOARDING CHECK
        # =========================
        if not user.profile_completed:
            return {
                "state": "ONBOARDING_REQUIRED",
                "score": {"score": 0},
                "level": "ONBOARDING"
            }

        # =========================
        # PROFILE
        # =========================
        profile = conn.execute(
            text("""
                SELECT *
                FROM user_profiles
                WHERE user_email = :email
            """),
            {"email": user_email}
        ).fetchone()

        profile_dict = dict(profile._mapping) if profile else {}

        # =========================
        # PORTFOLIO
        # =========================
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

        # =========================
        # FINANCIAL OVERVIEW
        # =========================
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
        # USER PROFILE CONTEXT
        # =========================
        user_profile = {
            **profile_dict,
            "portfolio": portfolio,
            "financial": financial,
            "score": score
        }

        # =========================
        # MODULE OPPORTUNITIES
        # =========================
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
        # GAMIFICATION
        # =========================
        streak = profile_dict.get("streak", 0)

        gamification = build_gamification(
            user,
            score,
            user.plan,
            streak
        )

        # =========================
        # RESULT
        # =========================
        result = {
            "user": user.email,
            "plan": user.plan,

            "score": score_data,
            "upgrade": upgrade,
            "features": features,
            "opportunities": opportunities,
            "dashboard": dashboard,
            "gamification": gamification,

            "portfolio_size": len(portfolio)
        }

        # =========================
        # CACHE STORE
        # =========================
        set_cache(cache_key, result, ttl=300)

        return result


# =========================
# COMPATIBILITY LAYER
# =========================
orchestrator = run_orchestrator
