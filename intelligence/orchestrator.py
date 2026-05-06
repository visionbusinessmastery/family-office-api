# =========================
# UNIFIED USER CONTEXT ENGINE V3
# =========================

from sqlalchemy import text
from database import engine

from intelligence.analyzers.family_office_score import compute_family_office_score
from intelligence.analyzers.financial_overview import get_user_financial_overview

from intelligence.upgrade_engine import compute_upgrade_decision
from intelligence.feature_engine import compute_feature_access
from intelligence.opportunity_engine import compute_opportunities
from intelligence.dashboard_engine import build_dashboard


# =========================
# SAFE HELPERS
# =========================
def safe_float(value):
    try:
        return float(value or 0)
    except:
        return 0.0


# =========================
# FETCH USER
# =========================
def get_user(conn, email: str):
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
        qty = safe_float(r.quantity)
        price = safe_float(r.purchase_price)

        portfolio.append({
            "asset_name": r.asset_name,
            "type": (r.category or "").lower(),
            "value": qty * price
        })

    return portfolio


# =========================
# NORMALIZE PROFILE
# =========================
def normalize_profile(profile: dict, portfolio: list):

    savings = safe_float(profile.get("savings") or profile.get("epargne"))
    investments = safe_float(profile.get("investments"))

    # fallback intelligent
    if investments == 0 and portfolio:
        investments = sum([a.get("value", 0) for a in portfolio])

    return {
        "savings": savings,
        "investments": investments,
        "risk_profile": (profile.get("risk_profile") or "medium").lower(),
        "plan": profile.get("plan", "FREE")
    }


# =========================
# MAIN ENGINE V3
# =========================
def run_user_context(user_email: str):

    with engine.begin() as conn:

        # =========================
        # USER
        # =========================
        user = get_user(conn, user_email)

        if not user:
            return {"error": "USER_NOT_FOUND"}

        if not user.profile_completed:
            return {
                "state": "ONBOARDING_REQUIRED",
                "score": {"score": 0},
                "level": "ONBOARDING"
            }

        # =========================
        # DATA FETCH
        # =========================
        raw_profile = get_profile(conn, user_email)
        portfolio = get_portfolio(conn, user.id)
        financial = get_user_financial_overview(user.id) or {}

        # =========================
        # NORMALIZATION
        # =========================
        profile = normalize_profile(raw_profile, portfolio)
        profile["plan"] = user.plan

        # =========================
        # SCORE
        # =========================
        score_data = compute_family_office_score(
            profile,
            portfolio,
            financial
        )

        score = score_data.get("score", 0)

        # =========================
        # BUSINESS ENGINES
        # =========================
        upgrade = compute_upgrade_decision(user.plan, score)
        features = compute_feature_access(profile, score_data)
        opportunities = compute_opportunities(profile, portfolio)

        # =========================
        # DASHBOARD
        # =========================
        dashboard = build_dashboard(
            {"plan": user.plan},
            {
                "score": score_data,
                "level": score_data.get("level", "BEGINNER")
            }
        )

        # =========================
        # FINAL PAYLOAD
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
