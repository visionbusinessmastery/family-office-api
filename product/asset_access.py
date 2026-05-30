from fastapi import HTTPException
from sqlalchemy import text

from product.entitlements import build_entitlements
from product.tiers import normalize_plan, resolve_effective_plan


DEPTH_LABELS = {
    "simple": "Lecture simple",
    "cashflow": "Cashflow et rendement",
    "structured": "Structure et KPI",
    "simulation": "Simulation et stress tests",
    "valuation": "Valorisation et scaling",
    "family_office": "Lecture Family Office",
    "dynasty": "Lecture Dynasty Office",
}


def get_effective_plan_and_entitlements(conn, user_id: int):
    row = conn.execute(text("""
        SELECT
            users.plan AS user_plan,
            subscriptions.plan AS subscription_plan,
            subscriptions.status AS subscription_status
        FROM users
        LEFT JOIN subscriptions ON subscriptions.user_id = users.id
        WHERE users.id = :user_id
    """), {"user_id": user_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    effective_plan = resolve_effective_plan(
        row.user_plan,
        row.subscription_plan,
        row.subscription_status,
    )
    return effective_plan, build_entitlements(effective_plan)


def build_asset_access(conn, user_id: int, domain: str, table_name: str):
    plan, entitlements = get_effective_plan_and_entitlements(conn, user_id)
    limit_key = f"max_{domain}_assets"
    depth_key = f"{domain}_depth"
    count = conn.execute(
        text(f"SELECT COUNT(*) FROM {table_name} WHERE user_id = :user_id"),
        {"user_id": user_id},
    ).scalar() or 0
    limit = entitlements.get(limit_key)
    depth = entitlements.get(depth_key) or "simple"

    return {
        "plan": normalize_plan(plan),
        "count": int(count),
        "limit": limit,
        "remaining": None if limit is None else max(int(limit) - int(count), 0),
        "depth": depth,
        "depth_label": DEPTH_LABELS.get(depth, depth),
        "is_unlimited": limit is None,
    }


def enforce_asset_creation_allowed(conn, user_id: int, domain: str, table_name: str):
    access = build_asset_access(conn, user_id, domain, table_name)
    limit = access.get("limit")

    if limit is not None and int(access["count"]) >= int(limit):
        domain_label = "immobiliers" if domain == "real_estate" else "business"
        raise HTTPException(
            status_code=403,
            detail=(
                f"Limite atteinte pour les actifs {domain_label}: "
                f"{access['count']}/{limit}. Change de plan pour ajouter une nouvelle ligne."
            ),
        )

    return access
