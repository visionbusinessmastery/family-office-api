from sqlalchemy import text

from core.cache import delete_cache_patterns, delete_cache_keys


BADGE_THRESHOLDS = [
    (50, "Fondations"),
    (150, "Architecte actif"),
    (300, "Investisseur structure"),
    (600, "Operateur patrimonial"),
    (1000, "Wealth Builder"),
]


def ensure_gamification_tables(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_gamification (
            user_id INTEGER PRIMARY KEY,
            xp INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            streak INTEGER NOT NULL DEFAULT 0,
            badges TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("ALTER TABLE user_gamification ADD COLUMN IF NOT EXISTS xp INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE user_gamification ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 1"))
    conn.execute(text("ALTER TABLE user_gamification ADD COLUMN IF NOT EXISTS streak INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE user_gamification ADD COLUMN IF NOT EXISTS badges TEXT DEFAULT ''"))
    conn.execute(text("ALTER TABLE user_gamification ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()"))
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS user_gamification_user_unique ON user_gamification(user_id)"))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS progression_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            xp INTEGER NOT NULL DEFAULT 0,
            level_name TEXT NOT NULL DEFAULT 'Builder',
            status TEXT NOT NULL DEFAULT 'Foundation',
            streak INTEGER NOT NULL DEFAULT 0,
            last_seen_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("ALTER TABLE progression_profiles ADD COLUMN IF NOT EXISTS xp INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE progression_profiles ADD COLUMN IF NOT EXISTS level_name TEXT NOT NULL DEFAULT 'Builder'"))
    conn.execute(text("ALTER TABLE progression_profiles ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'Foundation'"))
    conn.execute(text("ALTER TABLE progression_profiles ADD COLUMN IF NOT EXISTS streak INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("ALTER TABLE progression_profiles ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP"))
    conn.execute(text("ALTER TABLE progression_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()"))
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS progression_profiles_user_unique ON progression_profiles(user_id)"))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS xp_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("ALTER TABLE xp_events ADD COLUMN IF NOT EXISTS metadata JSONB"))


def level_from_xp(xp: int) -> int:
    return max(1, int(xp / 100) + 1)


def level_name_from_xp(xp: int) -> str:
    if xp >= 1000:
        return "Wealth Builder"
    if xp >= 600:
        return "Operator"
    if xp >= 300:
        return "Advanced"
    if xp >= 150:
        return "Builder"
    return "Beginner"


def badges_from_xp(xp: int, current_badges: str | None = "") -> str:
    badges = {item.strip() for item in (current_badges or "").split(",") if item.strip()}
    for threshold, badge in BADGE_THRESHOLDS:
        if xp >= threshold:
            badges.add(badge)
    return ",".join(sorted(badges))


def invalidate_gamification_caches(email: str | None, user_id: int | None):
    if email:
        delete_cache_patterns(
            f"gamification:{email}*",
            f"intel:{email}*",
            f"context:{email}*",
        )
    if user_id:
        delete_cache_keys(f"badges:{user_id}")


def award_xp(
    conn,
    user_id: int,
    email: str | None,
    event_type: str,
    xp_amount: int,
    metadata: dict | None = None,
):
    if not user_id or xp_amount <= 0:
        return {"awarded": 0}

    ensure_gamification_tables(conn)

    row = conn.execute(text("""
        SELECT xp, badges, streak
        FROM user_gamification
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchone()

    current_xp = int(row.xp or 0) if row else 0
    current_badges = row.badges if row else ""
    current_streak = int(row.streak or 0) if row else 0
    next_xp = current_xp + int(xp_amount)
    next_level = level_from_xp(next_xp)
    next_badges = badges_from_xp(next_xp, current_badges)

    conn.execute(text("""
        INSERT INTO user_gamification (user_id, xp, level, streak, badges, updated_at)
        VALUES (:user_id, :xp, :level, :streak, :badges, NOW())
        ON CONFLICT (user_id) DO UPDATE
        SET xp = EXCLUDED.xp,
            level = EXCLUDED.level,
            streak = GREATEST(user_gamification.streak, EXCLUDED.streak),
            badges = EXCLUDED.badges,
            updated_at = NOW()
    """), {
        "user_id": user_id,
        "xp": next_xp,
        "level": next_level,
        "streak": current_streak,
        "badges": next_badges,
    })

    conn.execute(text("""
        INSERT INTO progression_profiles (user_id, xp, level_name, status, streak, last_seen_at, updated_at)
        VALUES (:user_id, :xp, :level_name, 'Foundation', :streak, NOW(), NOW())
        ON CONFLICT (user_id) DO UPDATE
        SET xp = GREATEST(progression_profiles.xp, EXCLUDED.xp),
            level_name = EXCLUDED.level_name,
            streak = GREATEST(progression_profiles.streak, EXCLUDED.streak),
            last_seen_at = NOW(),
            updated_at = NOW()
    """), {
        "user_id": user_id,
        "xp": next_xp,
        "level_name": level_name_from_xp(next_xp),
        "streak": current_streak,
    })

    conn.execute(text("""
        INSERT INTO xp_events (user_id, event_type, xp, metadata)
        VALUES (:user_id, :event_type, :xp, CAST(:metadata AS JSONB))
    """), {
        "user_id": user_id,
        "event_type": event_type,
        "xp": int(xp_amount),
        "metadata": "{}" if metadata is None else __import__("json").dumps(metadata),
    })

    invalidate_gamification_caches(email, user_id)

    return {
        "awarded": int(xp_amount),
        "xp": next_xp,
        "level": next_level,
        "badges": next_badges.split(",") if next_badges else [],
    }
