# =========================
# AUTOPILOT V4 FULL ENGINE
# HEDGE FUND SIMULATION CORE
# =========================

from datetime import datetime
import uuid

from advisor.engine import detect_risk
from advisor.portfolio_ai import optimal_allocation


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
    # MAIN ENTRY
    # =========================
    def run(self, portfolio, market_signal, symbol="BTC", price=100):

        risk_level = detect_risk(str(market_signal))
        target_alloc = optimal_allocation(risk_level)

        # =========================
        # SIMULATE TRADE DECISION
        # =========================
        trade = self._generate_trade(symbol, price, market_signal, risk_level)

        # =========================
        # EXECUTION SIMULATION
        # =========================
        execution = self._execute_trade_simulation(trade, portfolio)

        # =========================
        # PERFORMANCE CALC
        # =========================
        performance = self._compute_performance(execution)

        # =========================
        # JOURNAL ENTRY
        # =========================
        journal_entry = self._log_decision(trade, execution, performance)

        return {
            "analysis": {
                "risk_level": risk_level,
                "market_signal": market_signal,
                "target_allocation": target_alloc
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

        # fake market movement simulation
        exit_price = entry_price * (1.02 if trade["direction"] == "BUY" else 0.98)

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
    # JOURNAL AI
    # =========================
    def _log_decision(self, trade, execution, performance):

        entry = {
            "trade": trade,
            "execution": execution,
            "performance_snapshot": performance,
            "timestamp": datetime.utcnow().isoformat()
        }

        TRADE_JOURNAL.append(entry)

        return entry


# =========================
# FACTORY
# =========================
def get_autopilot_v4():
    return AutopilotV4()
