from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from auth.utils import get_current_user
from database import engine
from feature_flags.engine import ensure_feature_flags_table, list_feature_flags
from security.audit import require_security_admin


router = APIRouter()


@router.get("/")
def get_feature_flags(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_feature_flags_table(conn)
        user = conn.execute(text("""
            SELECT id, email, plan, is_founder
            FROM users
            WHERE email = :email
        """), {"email": email}).fetchone()

        flags = list_feature_flags(conn)

    return {
        "flags": [
            {
                "key": row.key,
                "enabled": bool(row.enabled),
                "rollout_percentage": int(row.rollout_percentage or 0),
                "subscription_min": row.subscription_min,
                "founder_only": bool(row.founder_only),
                "beta_only": bool(row.beta_only),
                "user_visible": bool(user),
            }
            for row in flags
        ]
    }


@router.put("/{feature_key}")
def update_feature_flag(
    feature_key: str,
    data: dict,
    request: Request,
    email: str = Depends(get_current_user),
):
    with engine.begin() as conn:
        ensure_feature_flags_table(conn)
        require_security_admin(conn, email, request)
        conn.execute(text("""
            INSERT INTO feature_flags (
                key, enabled, rollout_percentage, subscription_min, founder_only, beta_only, updated_at
            )
            VALUES (
                :key, :enabled, :rollout_percentage, :subscription_min, :founder_only, :beta_only, NOW()
            )
            ON CONFLICT (key)
            DO UPDATE SET
                enabled = EXCLUDED.enabled,
                rollout_percentage = EXCLUDED.rollout_percentage,
                subscription_min = EXCLUDED.subscription_min,
                founder_only = EXCLUDED.founder_only,
                beta_only = EXCLUDED.beta_only,
                updated_at = NOW()
        """), {
            "key": feature_key,
            "enabled": bool(data.get("enabled")),
            "rollout_percentage": int(data.get("rollout_percentage", 0)),
            "subscription_min": str(data.get("subscription_min") or "FREE").upper(),
            "founder_only": bool(data.get("founder_only")),
            "beta_only": bool(data.get("beta_only")),
        })

    return {"status": "updated", "key": feature_key}
