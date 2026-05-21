from sqlalchemy import text

from auth.utils import get_user_id
from intelligence.core.orchestrator import run_orchestrator
from portfolio.service import get_user_portfolio
from product.entitlements import resolve_effective_plan


def centralized_user_state_builder(conn, email: str):
    user = conn.execute(text("""
        SELECT
            users.id,
            users.email,
            users.plan AS user_plan,
            users.level,
            subscriptions.plan AS subscription_plan,
            subscriptions.status AS subscription_status
        FROM users
        LEFT JOIN subscriptions ON subscriptions.user_id = users.id
        WHERE users.email = :email
    """), {"email": email}).fetchone()

    if not user:
        return {
            "user_id": None,
            "plan": "FREE",
            "level": None,
            "dashboard_context": {},
            "portfolio": {},
            "opportunities": [],
            "score": 0,
        }

    plan = resolve_effective_plan(
        user.user_plan,
        user.subscription_plan,
        user.subscription_status,
    )
    dashboard_context = run_orchestrator(email)
    dashboard_context["plan"] = plan
    dashboard_context["level"] = user.level
    portfolio = get_user_portfolio(user.id)
    opportunities = dashboard_context.get("opportunities", [])
    score = dashboard_context.get("global_score") or dashboard_context.get("score", 0)
    if isinstance(score, dict):
        score = score.get("score", 0)

    return {
        "user_id": user.id,
        "plan": plan,
        "level": user.level,
        "dashboard_context": dashboard_context,
        "portfolio": portfolio,
        "opportunities": opportunities,
        "score": score,
    }


def user_id_for_email(conn, email: str):
    return get_user_id(conn, email)
