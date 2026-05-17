# =========================
# AUTOPILOT V4 FULL ENGINE
# HEDGE FUND SIMULATION CORE
# =========================

from datetime import datetime
import uuid

# =========================
# MEMORY STORE (SIMPLIFIED)
# =========================
TRADE_JOURNAL = []
PERFORMANCE_LOG = []


# =========================
# ENGINE CLASS
# =========================
class AutopilotV4:

    # =========================
    # MAIN ENTRY POINT
    # =========================
    def run(self, user_email=None, portfolio=None, market=None, context=None, llm_analysis=None, level="free"):

        # fallback compatibility (ancien appel simplifié)
        market_signal = extract_score_signal(context)

        risk_level = detect_risk(str(market_signal))
        target_alloc = optimal_allocation(risk_level)

        # =========================
        # TRADE GENERATION
        # =========================
        trade = self._generate_trade(
            symbol="BTC",
            price=100,
            signal=market_signal,
            risk=risk_level
        )

        # =========================
        # EXECUTION SIMULATION
        # =========================
        execution = self._execute_trade_simulation(trade, portfolio)

        # =========================
        # PERFORMANCE
        # =========================
        performance = self._compute_performance(execution)

        # =========================
        # JOURNALING
        # =========================
        journal_entry = self._log_decision(trade, execution, performance, llm_analysis)

        return {
            "analysis": {
                "risk_level": risk_level,
                "market_signal": market_signal,
                "target_allocation": target_alloc,
                "llm_summary": llm_analysis
            },
            "trade": trade,
            "execution": execution,
            "performance": performance,
            "journal": journal_entry
        }

    # =========================
    # TRADE GENERATION
    # =========================
    def _generate_trade(self, symbol, price, signal, risk):

        direction = "BUY" if signal > 0.5 else "SELL"

        size_multiplier = {
            "low": 0.5,
            "medium": 1,
            "high": 1.5
        }.get(risk, 1)

        size = round(1000 * size_multiplier, 2)

        return {
            "id": str(uuid.uuid4()),
            "symbol": symbol,
            "direction": direction,
            "size": size,
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        }

    # =========================
    # SIMULATION ENGINE
    # =========================
    def _execute_trade_simulation(self, trade, portfolio):

        entry_price = trade["price"]

        # simulation marché
        exit_price = entry_price * (
            1.02 if trade["direction"] == "BUY" else 0.98
        )

        pnl = (exit_price - entry_price) * (trade["size"] / entry_price)

        result = {
            "entry": entry_price,
            "exit": round(exit_price, 2),
            "pnl": round(pnl, 2),
            "status": "CLOSED"
        }

        return result

    # =========================
    # PERFORMANCE TRACKING
    # =========================
    def _compute_performance(self, execution):

        PERFORMANCE_LOG.append(execution)

        wins = len([t for t in PERFORMANCE_LOG if t["pnl"] > 0])
        total = len(PERFORMANCE_LOG)

        winrate = (wins / total * 100) if total > 0 else 0

        total_pnl = sum([t["pnl"] for t in PERFORMANCE_LOG])

        return {
            "total_trades": total,
            "winrate": round(winrate, 2),
            "total_pnl": round(total_pnl, 2)
        }

    # =========================
    # JOURNAL ENGINE
    # =========================
    def _log_decision(self, trade, execution, performance, llm_analysis=None):

        entry = {
            "trade": trade,
            "execution": execution,
            "performance_snapshot": performance,
            "ai_summary": llm_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }

        TRADE_JOURNAL.append(entry)

        return entry


def detect_risk(signal: str):
    try:
        s = float(signal)
    except:
        s = 0.5

    if s < 0.3:
        return "low"
    elif s < 0.7:
        return "medium"
    else:
        return "high"


def extract_score_signal(context):
    if not isinstance(context, dict):
        return 0.5

    raw_score = context.get("global_score") or context.get("score", 0.5)

    if isinstance(raw_score, dict):
        raw_score = raw_score.get("score", 50)

    try:
        score = float(raw_score)
    except:
        return 0.5

    return score / 100 if score > 1 else score

# =========================
# FACTORY FUNCTION
# =========================
def get_autopilot_v4():
    return AutopilotV4()
