from sqlalchemy import text


def ensure_ethan_observability_tables(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ethan_cost_analytics (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            email TEXT,
            plan TEXT,
            module TEXT,
            feature TEXT,
            model TEXT,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            estimated_cost_usd NUMERIC DEFAULT 0,
            latency_ms NUMERIC DEFAULT 0,
            cache_hit BOOLEAN DEFAULT FALSE,
            prompt_type TEXT,
            failed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ethan_cost_analytics_created
        ON ethan_cost_analytics(created_at DESC)
    """))


def cost_by_day(conn, days: int = 30):
    return conn.execute(text("""
        SELECT created_at::date AS day,
               plan,
               model,
               COUNT(*) AS requests,
               COALESCE(SUM(input_tokens), 0) AS input_tokens,
               COALESCE(SUM(output_tokens), 0) AS output_tokens,
               COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
               COALESCE(SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END), 0) AS cache_hits
        FROM ethan_usage_events
        WHERE created_at >= NOW() - (:days * interval '1 day')
        GROUP BY day, plan, model
        ORDER BY day DESC, estimated_cost_usd DESC
    """), {"days": days}).fetchall()


def cost_by_plan(conn, days: int = 30):
    return conn.execute(text("""
        SELECT plan,
               COUNT(*) AS requests,
               COUNT(DISTINCT user_id) AS users,
               COALESCE(SUM(input_tokens), 0) AS input_tokens,
               COALESCE(SUM(output_tokens), 0) AS output_tokens,
               COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
               COALESCE(SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END), 0) AS cache_hits
        FROM ethan_usage_events
        WHERE created_at >= NOW() - (:days * interval '1 day')
        GROUP BY plan
        ORDER BY estimated_cost_usd DESC
    """), {"days": days}).fetchall()


def cost_by_model(conn, days: int = 30):
    return conn.execute(text("""
        SELECT model,
               COUNT(*) AS requests,
               COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
               COALESCE(SUM(input_tokens), 0) AS input_tokens,
               COALESCE(SUM(output_tokens), 0) AS output_tokens
        FROM ethan_usage_events
        WHERE created_at >= NOW() - (:days * interval '1 day')
        GROUP BY model
        ORDER BY estimated_cost_usd DESC
    """), {"days": days}).fetchall()


def top_expensive_users(conn, days: int = 30):
    return conn.execute(text("""
        SELECT email, plan,
               COUNT(*) AS requests,
               COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd
        FROM ethan_usage_events
        WHERE created_at >= NOW() - (:days * interval '1 day')
        GROUP BY email, plan
        ORDER BY estimated_cost_usd DESC
        LIMIT 20
    """), {"days": days}).fetchall()
