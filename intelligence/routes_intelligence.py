# =========================
# INTELLIGENCE ROUTES V3 (PRODUCTION READY)
# =========================

from fastapi import APIRouter, Depends, Request
from auth.utils import get_current_user

from intelligence.user_intelligence_engine import compute_user_intelligence
from intelligence.dashboard_engine import build_dashboard
from intelligence.upgrade_engine import compute_upgrade_decision

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


# =========================
# FULL USER INTELLIGENCE (CORE API)
# =========================
@router.get("/me")
def get_my_intelligence(user=Depends(get_current_user)):

    user_email = user

    data = compute_user_intelligence(user_email)

    if not data or "error" in data:
        return {"error": "INTELLIGENCE_FAILED"}

    return data


# =========================
# LIGHT VERSION (FAST DASHBOARD)
# =========================
@router.get("/summary")
def get_summary(user=Depends(get_current_user)):

    user_email = user

    data = compute_user_intelligence(user_email)

    return {
        "score": data.get("score", {}).get("score", 0),
        "level": data.get("level"),
        "plan": data.get("plan"),
        "upgrade": data.get("upgrade"),
    }


# =========================
# DASHBOARD ONLY
# =========================
@router.get("/dashboard")
def get_dashboard(user=Depends(get_current_user)):

    user_email = user

    data = compute_user_intelligence(user_email)

    dashboard = build_dashboard(
        {
            "plan": data.get("plan")
        },
        data
    )

    return {
        "dashboard": dashboard,
        "score": data.get("score"),
        "features": data.get("features")
    }


# =========================
# UPGRADE CHECK
# =========================
@router.get("/upgrade")
def check_upgrade(user=Depends(get_current_user)):

    user_email = user

    data = compute_user_intelligence(user_email)

    score = data.get("score", {}).get("score", 0)
    plan = data.get("plan")

    upgrade = compute_upgrade_decision(plan, score)

    return {
        "current_plan": plan,
        "score": score,
        "upgrade": upgrade
    }


# =========================
# OPPORTUNITIES ONLY
# =========================
@router.get("/opportunities")
def get_opportunities(user=Depends(get_current_user)):

    user_email = user

    data = compute_user_intelligence(user_email)

    return {
        "opportunities": data.get("opportunities", [])
    }


# =========================
# FEATURES ACCESS
# =========================
@router.get("/features")
def get_features(user=Depends(get_current_user)):

    user_email = user

    data = compute_user_intelligence(user_email)

    return {
        "features": data.get("features", [])
    }
