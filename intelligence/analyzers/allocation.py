def allocate_portfolio(query=None, real=None, crypto=None, stocks=None):
    """
    Simple allocation engine based on risk profile.
    """

    # =========================
    # SAFE RISK EXTRACTION
    # =========================
    risk = ""

    if query and hasattr(query, "risk"):
        risk = query.risk or ""
    elif isinstance(query, dict):
        risk = query.get("risk", "") or ""

    risk = str(risk).strip().lower()

    # =========================
    # ALLOCATION LOGIC
    # =========================
    if risk in ["faible", "low"]:
        allocation = {
            "real_estate": 60,
            "stocks": 30,
            "crypto": 10
        }

    elif risk in ["modéré", "modere", "medium", "moderate"]:
        allocation = {
            "real_estate": 40,
            "stocks": 40,
            "crypto": 20
        }

    else:
        allocation = {
            "real_estate": 20,
            "stocks": 40,
            "crypto": 40
        }

    # =========================
    # FUTURE SAFE OVERRIDE (OPTIONNEL)
    # =========================
    if real is not None:
        allocation["real_estate"] = real
    if stocks is not None:
        allocation["stocks"] = stocks
    if crypto is not None:
        allocation["crypto"] = crypto

    return allocation
