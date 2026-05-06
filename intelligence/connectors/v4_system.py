# =========================
# CONNECT V4 SYSTEM
# UNIFIED AI FAMILY OFFICE CORE
# =========================

from advisor.autopilot_v4 import get_autopilot_v4
from intelligence.user_intelligence_engine import compute_user_intelligence
from intelligence.dashboard_engine import build_dashboard


# =========================
# GLOBAL ENGINE INSTANCE
# =========================
autopilot = get_autopilot_v4()


# =========================
# MAIN ENTRY (BRAIN SYSTEM)
# =========================
def run_v4_system(user_email, portfolio, market_signal, symbol="BTC", price=100):

    # =========================
    # 1. USER INTELLIGENCE
    # =========================
    intelligence = compute_user_intelligence(user_email)

    # =========================
    # 2. AUTOPILOT EXECUTION
    # =========================
    autopilot_result = autopilot.run(
        portfolio=portfolio,
        market_signal=market_signal,
        symbol=symbol,
        price=price
    )

    # =========================
    # 3. DASHBOARD BUILD
    # =========================
    dashboard = build_dashboard(
        user={"plan": intelligence.get("plan", "FREE")},
        intelligence=intelligence
    )

    # =========================
    # 4. FINAL PAYLOAD (API READY)
    # =========================
    return {
        "user": user_email,
        "intelligence": intelligence,

        "autopilot": {
            "analysis": autopilot_result["analysis"],
            "trade": autopilot_result["trade"],
            "performance": autopilot_result["performance"],
            "journal": autopilot_result["journal"]
        },

        "dashboard": dashboard,

        "system": "V4_CONNECTOR_ACTIVE"
    }
