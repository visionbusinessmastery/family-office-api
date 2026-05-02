from advisor.portfolio_ai import (
    score_portfolio,
    generate_actions,
    optimal_allocation
)

from advisor.risk import compute_risk_metrics
from advisor.memory import get_memory, update_memory


def detect_drift(current_alloc, target_alloc):

    drift = {}

    for asset in target_alloc:
        current = current_alloc.get(asset, 0)
        target = target_alloc.get(asset, 0)

        drift[asset] = round(current - target, 2)

    return drift


def should_rebalance(drift):

    for v in drift.values():
        if abs(v) > 10:
            return True

    return False


def autopilot_engine(user_email, portfolio, market, risk_level):

    memory = get_memory(user_email)

    # =========================
    # 1. SCORE + RISK
    # =========================
    score = score_portfolio(portfolio, market)
    risk_metrics = compute_risk_metrics(portfolio)

    # =========================
    # 2. TARGET ALLOCATION
    # =========================
    target_alloc = optimal_allocation(risk_level)

    current_alloc = portfolio.get("allocation", {})

    drift = detect_drift(current_alloc, target_alloc)

    rebalance = should_rebalance(drift)

    # =========================
    # 3. DECISION ENGINE
    # =========================
    actions = generate_actions(score)

    if rebalance:
        actions.append("FORCE_REBALANCE")

    if risk_metrics["risk_level"] == "high":
        actions.append("REDUCE_EXPOSURE")

    # =========================
    # 4. MEMORY UPDATE
    # =========================
    update_memory(user_email, {
        "last_score": score,
        "last_allocation": target_alloc
    })

    return {
        "score": score,
        "risk": risk_metrics,
        "drift": drift,
        "rebalance": rebalance,
        "actions": actions,
        "target_allocation": target_alloc
    }
