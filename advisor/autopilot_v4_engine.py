from datetime import datetime


SIMULATION_UNAVAILABLE = {
    "status": "unavailable",
    "role": "SIMULATION SATELLITE ONLY",
    "message": "simulation unavailable without external market context",
}


class AutopilotV4:
    """
    Simulation satellite only.

    This module never interprets user intent, never produces advice, and never
    makes trade or allocation decisions. Ethan cognition remains exclusively
    in advisor/service.py.
    """

    def run(self, user_email=None, portfolio=None, market=None, context=None, llm_analysis=None, level="free"):
        scenario = self._extract_market_scenario(market)
        if not scenario:
            return dict(SIMULATION_UNAVAILABLE)

        return {
            "status": "ready",
            "role": "SIMULATION SATELLITE ONLY",
            "authority": "no_decision_authority",
            "simulation_context": {
                "user_email": user_email,
                "level": level,
                "portfolio_snapshot": portfolio or {},
                "context_snapshot": context or {},
            },
            "market_scenario": scenario,
            "outputs": {
                "decision": None,
                "trade": None,
                "recommendation": None,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _extract_market_scenario(self, market):
        if not isinstance(market, dict) or not market:
            return None

        scenario = market.get("scenario") or market.get("market_scenario")
        if isinstance(scenario, dict) and scenario:
            return scenario

        signals = market.get("signals") or market.get("data")
        if isinstance(signals, dict) and signals:
            return {"signals": signals}

        return None


def get_autopilot_v4():
    return AutopilotV4()
