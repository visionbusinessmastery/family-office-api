# =========================
# COMPUTE OPPORTUNITIES (PRODUCTION READY)
# =========================

def compute_opportunities(profile: dict, portfolio: list):
    """
    Génère des opportunités d'investissement personnalisées
    basé sur profil + portefeuille utilisateur.
    """

    opportunities = []

    # =========================
    # SAFE INPUTS
    # =========================
    if not isinstance(profile, dict):
        profile = {}

    if not isinstance(portfolio, list):
        portfolio = []

    risk = (profile.get("risk_profile") or "medium").lower().strip()

    savings = float(profile.get("savings") or 0)

    investments = float(profile.get("investments") or 0)

    total_assets = savings + investments

    # =========================
    # 1. REAL ESTATE OPPORTUNITY
    # =========================
    if savings >= 20000:

        priority = "high" if savings >= 50000 else "medium"

        opportunities.append({
            "type": "real_estate",
            "title": "Opportunité immobilière",
            "description": "Investissement locatif potentiel détecté avec cash disponible",
            "priority": priority
        })

    # =========================
    # 2. CRYPTO OPPORTUNITY
    # =========================
    if risk in ["medium", "high"]:

        crypto_priority = "high" if risk == "high" else "medium"

        opportunities.append({
            "type": "crypto",
            "title": "Signal crypto marché",
            "description": "Exposition crypto recommandée (BTC / ETH / DCA)",
            "priority": crypto_priority
        })

    # =========================
    # 3. BUSINESS OPPORTUNITY
    # =========================
    if savings >= 10000 or total_assets >= 15000:

        opportunities.append({
            "type": "business",
            "title": "Business scalable détecté",
            "description": "Création ou investissement business digital recommandé",
            "priority": "medium"
        })

    # =========================
    # 4. PORTFOLIO DIVERSIFICATION
    # =========================
    asset_types = set()

    for asset in portfolio:
        try:
            t = (asset.get("type") or "").lower()
            if t:
                asset_types.add(t)
        except:
            continue

    if len(asset_types) <= 2:

        opportunities.append({
            "type": "diversification",
            "title": "Diversification portefeuille",
            "description": "Ton portefeuille manque de diversification",
            "priority": "high"
        })

    # =========================
    # SORT BY PRIORITY
    # =========================
    priority_order = {
        "high": 3,
        "medium": 2,
        "low": 1
    }

    opportunities.sort(
        key=lambda x: priority_order.get(x.get("priority", "low"), 0),
        reverse=True
    )

    return opportunities
