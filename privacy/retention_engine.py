from datetime import datetime

from sqlalchemy import text

from privacy.routes import ensure_privacy_tables, log_privacy_event


RETENTION_RULES = {
    "ethan_memory": "12 months",
    "ethan_usage_events": "90 days",
    "notifications": "6 months",
    "user_data_exports": "7 days",
}


def run_retention_purge(conn):
    ensure_privacy_tables(conn)

    results = {}

    operations = [
        (
            "ethan_memory",
            "DELETE FROM ethan_memory WHERE updated_at < NOW() - interval '12 months'",
        ),
        (
            "ethan_usage_events",
            "DELETE FROM ethan_usage_events WHERE created_at < NOW() - interval '90 days'",
        ),
        (
            "notifications",
            "DELETE FROM notifications WHERE created_at < NOW() - interval '6 months'",
        ),
        (
            "user_data_exports",
            "DELETE FROM user_data_exports WHERE expires_at < NOW()",
        ),
    ]

    for key, query in operations:
        try:
            result = conn.execute(text(query))
            results[key] = result.rowcount
        except Exception as exc:
            results[key] = f"skipped: {exc}"

    due_requests = conn.execute(text("""
        SELECT id, user_id
        FROM user_deletion_requests
        WHERE status = 'confirmed' AND scheduled_for <= NOW()
        LIMIT 50
    """)).fetchall()

    for request in due_requests:
        user_id = request.user_id
        for table in [
            "ethan_memory",
            "portfolio",
            "real_estate_assets",
            "yield_assets",
            "venture_assets",
            "notifications",
            "progression_profiles",
            "xp_events",
            "legacy_family_vault",
            "legacy_heirs",
            "legacy_governance_rules",
            "legacy_metrics",
            "user_wealth_profiles",
            "privacy_preferences",
            "oauth_accounts",
            "oauth_login_sessions",
        ]:
            try:
                conn.execute(text(f"DELETE FROM {table} WHERE user_id = :user_id"), {"user_id": user_id})
            except Exception:
                pass

        conn.execute(text("""
            UPDATE users
            SET email = CONCAT('deleted+', id, '@white-rock.local'),
                password_hash = NULL,
                profile_completed = FALSE,
                revenus_mensuels = 0,
                charges_mensuelles = 0
            WHERE id = :user_id
        """), {"user_id": user_id})

        conn.execute(text("""
            UPDATE user_deletion_requests
            SET status = 'completed', completed_at = NOW()
            WHERE id = :id
        """), {"id": request.id})
        log_privacy_event(conn, user_id, "account_deletion_completed", {}, None)

    results["deletion_requests_completed"] = len(due_requests)
    results["ran_at"] = datetime.utcnow().isoformat()
    return results
