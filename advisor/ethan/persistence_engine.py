import json

from sqlalchemy import text

from advisor.ethan.runtime_engine import estimate_cost
from core.cache import redis_client
from product.entitlements import resolve_effective_plan


_ethan_schema_ready = False


def ensure_ethan_ai_tables(conn):
    global _ethan_schema_ready

    if _ethan_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ethan_memory (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            strategic_summary TEXT,
            session_summary TEXT,
            last_topic TEXT,
            context_profile JSONB,
            key_signals TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    conn.execute(text("ALTER TABLE ethan_memory ADD COLUMN IF NOT EXISTS context_profile JSONB"))
    conn.execute(text("ALTER TABLE ethan_memory ADD COLUMN IF NOT EXISTS key_signals TEXT"))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ethan_usage_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            email TEXT,
            plan TEXT,
            tier TEXT,
            task_type TEXT,
            complexity TEXT,
            model TEXT,
            cache_hit BOOLEAN DEFAULT FALSE,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            estimated_cost_usd NUMERIC DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ethan_usage_events_user_day_idx
        ON ethan_usage_events(user_id, created_at)
    """))

    _ethan_schema_ready = True


def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass
    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def get_user_plan(conn, email):
    row = conn.execute(text("""
        SELECT
            users.id,
            users.plan AS user_plan,
            subscriptions.plan AS subscription_plan,
            subscriptions.status AS subscription_status
        FROM users
        LEFT JOIN subscriptions ON subscriptions.user_id = users.id
        WHERE users.email = :email
    """), {"email": email}).fetchone()

    if not row:
        return None, "FREE"

    return row.id, resolve_effective_plan(
        row.user_plan,
        row.subscription_plan,
        row.subscription_status,
    )


def get_daily_deep_usage(conn, user_id):
    if not user_id:
        return 0

    return int(conn.execute(text("""
        SELECT COUNT(*)
        FROM ethan_usage_events
        WHERE user_id = :user_id
          AND complexity = 'high'
          AND cache_hit = FALSE
          AND created_at::date = CURRENT_DATE
    """), {"user_id": user_id}).scalar() or 0)


def record_usage(
    conn,
    user_id,
    email,
    plan,
    tier,
    task_type,
    complexity,
    model,
    cache_hit,
    input_tokens=0,
    output_tokens=0,
):
    conn.execute(text("""
        INSERT INTO ethan_usage_events (
            user_id, email, plan, tier, task_type, complexity, model, cache_hit,
            input_tokens, output_tokens, estimated_cost_usd
        )
        VALUES (
            :user_id, :email, :plan, :tier, :task_type, :complexity, :model,
            :cache_hit, :input_tokens, :output_tokens, :estimated_cost_usd
        )
    """), {
        "user_id": user_id,
        "email": email,
        "plan": plan,
        "tier": tier,
        "task_type": task_type,
        "complexity": complexity,
        "model": model,
        "cache_hit": cache_hit,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": estimate_cost(model, input_tokens, output_tokens),
    })
