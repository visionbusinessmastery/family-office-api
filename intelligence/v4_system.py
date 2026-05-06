# =========================
# V4 CONNECTED SYSTEM
# AI FAMILY OFFICE CORE ENGINE
# =========================

from datetime import datetime
import uuid

from advisor.engine import run_advisor
from advisor.autopilot_v4_engine import get_autopilot_v4


# =========================
# GLOBAL STATE (SIMPLE SaaS MEMORY LAYER)
# =========================
SYSTEM_LOGS = []
PERFORMANCE_DB = {}


# =========================
# JOURNAL SYSTEM (CENTRAL LOGS)
# =========================
def log_event(user_email, event_type, payload):

    entry = {
        "id": str(uuid.uuid4()),
        "user": user_email,
        "type": event_type,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat()
    }

    SYSTEM_LOGS.append(entry)

    return entry


# =========================
# PERFORMANCE TRACKER GLOBAL
# =========================
def update_performance(user_email, trade_result):

    if user_email not in PERFORMANCE_DB:
        PERFORMANCE_DB[user_email] = {
            "pnl": 0,
            "trades": 0,
            "wins": 0,
            "losses": 0
        }

    db = PERFORMANCE_DB[user_email]

    pnl = trade_result.get("performance", {}).get("total_pnl", 0)

    db["pnl"] += pnl
    db["trades"] += 1

    if pnl > 0:
        db["wins"] += 1
    else:
        db["losses"] += 1

    return db


# =========================
# ADVISOR → STRATEGY LAYER
# =========================
def advisor_layer(user_email, message):

    decision = run_advisor(user_email, message)

    log_event(user_email, "ADVISOR_DECISION", decision)

    return decision


# =========================
# AUTOPILOT EXECUTION LAYER
# =========================
def autopilot_layer(user_email, message):

    autopilot = get_autopilot_v4()

    # simulate portfolio (placeholder safe structure)
    portfolio = [{"value": 10000}]

    market_signal = 0.6  # placeholder (à brancher plus tard market engine)

    result = autopilot.run(
        portfolio=portfolio,
        market_signal=market_signal,
        symbol="BTC",
        price=100
    )

    log_event(user_email, "AUTOPILOT_EXECUTION", result)

    update_performance(user_email, result)

    return result


# =========================
# FULL PIPELINE (CORE SaaS API)
# =========================
def run_v4_system(user_email, message, mode="advisor"):

    # =========================
    # 1. ADVISOR MODE
    # =========================
    if mode == "advisor":

        result = advisor_layer(user_email, message)

        return {
            "mode": "ADVISOR",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    # =========================
    # 2. AUTOPILOT MODE
    # =========================
    if mode == "autopilot":

        result = autopilot_layer(user_email, message)

        return {
            "mode": "AUTOPILOT_SIMULATION",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    # =========================
    # 3. FULL PIPELINE MODE (ADVISOR + EXECUTION)
    # =========================
    if mode == "full":

        advisor = advisor_layer(user_email, message)
        autopilot = autopilot_layer(user_email, message)

        return {
            "mode": "FULL_SYSTEM",
            "advisor": advisor,
            "autopilot": autopilot,
            "logs": SYSTEM_LOGS[-10:],
            "performance": PERFORMANCE_DB.get(user_email, {})
        }

    return {
        "error": "invalid mode"
    }


# =========================
# DASHBOARD API READY
# =========================
def get_user_dashboard(user_email):

    return {
        "user": user_email,
        "performance": PERFORMANCE_DB.get(user_email, {}),
        "recent_logs": [log for log in SYSTEM_LOGS if log["user"] == user_email][-10:]
    }
