# =========================
# ORCHESTRATOR V3 - CORE ENGINE
# =========================

from sqlalchemy import text
from database import engine

from intelligence.user_intelligence_engine import compute_user_intelligence
from intelligence.dashboard_engine import build_dashboard
from intelligence.analyzers.family_office_score import compute_family_office_score
from intelligence.upgrade_engine import compute_upgrade_decision
from intelligence.feature_engine import compute_feature_access
from intelligence.opportunity_engine import compute_opportunities

from intelligence.analyzers.financial_overview import get_user_financial_overview


# =========================
# SAFE FETCH USER
# =========================
def get_user_by_email(conn, email: str):
    return conn.execute(
        text("""
            SELECT id, email, plan, profile_completed
            FROM users
            WHERE email = :email
        """),
        {"email": email}
    ).fetchone()


# =========================
# FETCH PROFILE
# =========================
def get_profile(conn, email: str):
    row = conn.execute(
        text("""
            SELECT *
            FROM user_profiles
            WHERE user_email = :email
        """),
        {"email": email}
    ).fetchone()

    return dict(row._mapping) if row else {}


# =========================
# FETCH PORTFOLIO
# =========================
def get_portfolio(conn, user_id: int):

    rows = conn.execute(
        text("""
            SELECT asset_name, category, quantity, purchase_price
            FROM portfolio
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).fetchall()

    portfolio = []

    for r in rows:
        qty = float(r.quantity or 0)
        price = float(r.purchase_price or 0)

        portfolio.append({
            "asset_name": r.asset_name,
            "type": (r.category or "").lower(),
            "value": qty * price
        })

    return portfolio


# =========================
# MAIN ORCHESTRATION ENGINE
# =========================
def run_orchestrator(user_email: str):

    with engine.begin() as conn:

        # =========================
        # USER
        # =========================
        user = get_user_by_email(conn, user_email)

        if not user:
            return {"error": "USER_NOT_FOUND"}

        # =========================
        # PROFILE + PORTFOLIO
        # =========================
        profile = get_profile(conn, user_email)
        portfolio = get_portfolio(conn, user.id)

        financial = get_user_financial_overview(user.id) or {}

        # =========================
        # SCORE ENGINE
        # =========================
        score_data = compute_family_office_score(
            profile,
            portfolio,
            financial
        )

        score = score_data.get("score", 0)

        # =========================
        # UPGRADE ENGINE
        # =========================
        upgrade = compute_upgrade_decision(user.plan, score)

        # =========================
        # FEATURES ENGINE
        # =========================
        features = compute_feature_access(profile, score_data)

        # =========================
        # OPPORTUNITIES ENGINE
        # =========================
        opportunities = compute_opportunities(profile, portfolio)

        # =========================
        # DASHBOARD ENGINE
        # =========================
        dashboard = build_dashboard(
            {
                "plan": user.plan
            },
            {
                "score": score_data,
                "level": upgrade.get("recommended_plan", "FREE")
            }
        )

        # =========================
        # RETURN MASTER PAYLOAD
        # =========================
        return {
            "user": user.email,
            "plan": user.plan,

            "score": score_data,
            "upgrade": upgrade,
            "features": features,
            "opportunities": opportunities,
            "dashboard": dashboard,

            "portfolio_size": len(portfolio)
        }
