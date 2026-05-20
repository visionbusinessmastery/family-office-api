import hashlib

from sqlalchemy import text

from feature_flags.registry import DEFAULT_FLAGS
from product.entitlements import plan_allows


_feature_flags_ready = False


def ensure_feature_flags_table(conn):
    global _feature_flags_ready
    if _feature_flags_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS feature_flags (
            id SERIAL PRIMARY KEY,
            key TEXT NOT NULL UNIQUE,
            enabled BOOLEAN NOT NULL DEFAULT FALSE,
            rollout_percentage INTEGER NOT NULL DEFAULT 0,
            subscription_min TEXT NOT NULL DEFAULT 'FREE',
            founder_only BOOLEAN NOT NULL DEFAULT FALSE,
            beta_only BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    for key, config in DEFAULT_FLAGS.items():
        conn.execute(text("""
            INSERT INTO feature_flags (
                key, enabled, rollout_percentage, subscription_min, founder_only, beta_only
            )
            VALUES (
                :key, :enabled, :rollout_percentage, :subscription_min, :founder_only, :beta_only
            )
            ON CONFLICT (key) DO NOTHING
        """), {
            "key": key,
            "enabled": bool(config.get("enabled")),
            "rollout_percentage": int(config.get("rollout_percentage", 0)),
            "subscription_min": config.get("subscription_min", "FREE"),
            "founder_only": bool(config.get("founder_only", False)),
            "beta_only": bool(config.get("beta_only", False)),
        })

    _feature_flags_ready = True


def _rollout_bucket(feature_key: str, user_id: int | None, email: str | None):
    identity = f"{feature_key}:{user_id or email or 'anonymous'}"
    return int(hashlib.sha256(identity.encode()).hexdigest()[:8], 16) % 100


def is_feature_enabled(conn, feature_key: str, user: dict | None = None):
    ensure_feature_flags_table(conn)
    row = conn.execute(text("""
        SELECT key, enabled, rollout_percentage, subscription_min, founder_only, beta_only
        FROM feature_flags
        WHERE key = :key
    """), {"key": feature_key}).fetchone()

    if not row or not row.enabled:
        return False

    user = user or {}
    plan = user.get("plan", "FREE")
    if not plan_allows(plan, row.subscription_min):
        return False

    if row.founder_only and not user.get("is_founder"):
        return False

    if row.beta_only and not user.get("beta_access"):
        return False

    return _rollout_bucket(feature_key, user.get("id"), user.get("email")) < int(row.rollout_percentage or 0)


def list_feature_flags(conn):
    ensure_feature_flags_table(conn)
    return conn.execute(text("""
        SELECT key, enabled, rollout_percentage, subscription_min, founder_only, beta_only, updated_at
        FROM feature_flags
        ORDER BY key
    """)).fetchall()
