# =========================
# OPPORTUNITY ENGINE V2
# =========================

import json
import hashlib

from core.cache import redis_client
from product.entitlements import normalize_plan, plan_allows


# =========================
# CACHE HELPERS
# =========================
def get_cache(key):

    try:

        if redis_client:

            data = redis_client.get(key)

            if data:
                return json.loads(data)

    except:
        pass

    return None


def set_cache(key, value, ttl=300):

    try:

        if redis_client:

            redis_client.setex(
                key,
                ttl,
                json.dumps(value)
            )

    except:
        pass


# =========================
# HASH BUILDER
# =========================
def build_hash(profile, portfolio):

    raw = json.dumps({
        "profile": profile,
        "portfolio": portfolio
    }, sort_keys=True)

    return hashlib.md5(
        raw.encode()
    ).hexdigest()


# =========================
# SAFE FLOAT
# =========================
def safe_float(value):

    try:
        return float(value or 0)
    except:
        return 0


# =========================
# MAIN ENGINE
# =========================
def compute_opportunities(
    profile: dict,
    portfolio: list
):

    # =========================
    # SAFE INPUTS
    # =========================
    if not isinstance(profile, dict):
        profile = {}

    if not isinstance(portfolio, list):
        portfolio = []

    # =========================
    # CACHE KEY
    # =========================
    cache_hash = build_hash(
        profile,
        portfolio
    )

    cache_key = (
        f"opportunities:"
        f"{cache_hash}"
    )

    # =========================
    # CACHE CHECK
    # =========================
    cached = get_cache(cache_key)

    if cached:
        return cached

    opportunities = []

    # =========================
    # PROFILE DATA
    # =========================
    risk = (
        profile.get("risk_profile")
        or "medium"
    ).lower().strip()

    savings = safe_float(
        profile.get("savings")
    )

    investments = safe_float(
        profile.get("investments")
    )

    plan = normalize_plan(profile.get("plan"))

    total_assets = (
        savings + investments
    )

    # =========================
    # PORTFOLIO ANALYTICS
    # =========================
    asset_types = set()

    crypto_exposure = 0

    stock_exposure = 0

    total_portfolio = 0

    for asset in portfolio:

        if not isinstance(asset, dict):
            continue

        asset_type = (
            asset.get("type")
            or ""
        ).lower()

        value = safe_float(
            asset.get("value")
        )

        total_portfolio += value

        if asset_type:
            asset_types.add(asset_type)

        if asset_type == "crypto":
            crypto_exposure += value

        elif asset_type in [
            "stocks",
            "stock",
            "equity"
        ]:
            stock_exposure += value

    crypto_ratio = (
        crypto_exposure / total_portfolio
        if total_portfolio > 0 else 0
    )

    # =========================
    # REAL ESTATE
    # =========================
    if savings >= 20000:

        priority = (
            "high"
            if savings >= 50000
            else "medium"
        )

        opportunities.append({

            "type":
                "real_estate",

            "title":
                "Opportunité immobilière",

            "description":
                "Investissement locatif potentiel détecté",

            "priority":
                priority,

            "score":
                85 if priority == "high"
                else 65,

            "premium":
                False,
        })

    # =========================
    # CRYPTO
    # =========================
    if risk in ["medium", "high"]:

        crypto_priority = (
            "high"
            if risk == "high"
            else "medium"
        )

        opportunities.append({

            "type":
                "crypto",

            "title":
                "Signal crypto marché",

            "description":
                "Exposition crypto optimisable",

            "priority":
                crypto_priority,

            "score":
                90 if risk == "high"
                else 70,

            "premium":
                False,
        })

    # =========================
    # BUSINESS
    # =========================
    if (
        savings >= 10000
        or total_assets >= 15000
    ):

        opportunities.append({

            "type":
                "business",

            "title":
                "Business scalable détecté",

            "description":
                "Business digital fortement recommandé",

            "priority":
                "medium",

            "score":
                75,

            "premium":
                False,
        })

    # =========================
    # DIVERSIFICATION
    # =========================
    if len(asset_types) <= 2:

        opportunities.append({

            "type":
                "diversification",

            "title":
                "Diversification portefeuille",

            "description":
                "Portefeuille insuffisamment diversifié",

            "priority":
                "high",

            "score":
                88,

            "premium":
                False,
        })

    # =========================
    # PREMIUM AI SIGNALS
    # =========================
    if plan_allows(plan, "ELITE"):

        if crypto_ratio > 0.60:

            opportunities.append({

                "type":
                    "ai_rebalance",

                "title":
                    "Reequilibrage Ethan",

                "description":
                    "Concentration crypto excessive détectée",

                "priority":
                    "high",

                "score":
                    95,

                "premium":
                    True,
            })

        if total_assets >= 100000:

            opportunities.append({

                "type":
                    "private_equity",

                "title":
                    "Private Equity Access",

                "description":
                    "Eligible à des investissements privés",

                "priority":
                    "high",

                "score":
                    92,

                "premium":
                    True,
            })

    # =========================
    # REMOVE DUPLICATES
    # =========================
    unique = {}

    for opp in opportunities:

        unique[
            opp["type"]
        ] = opp

    opportunities = list(
        unique.values()
    )

    # =========================
    # SORTING
    # =========================
    opportunities.sort(
        key=lambda x: x.get(
            "score",
            0
        ),
        reverse=True
    )

    # =========================
    # FINAL PAYLOAD
    # =========================
    result = {

        "count":
            len(opportunities),

        "opportunities":
            opportunities,

        "analytics": {

            "crypto_ratio":
                round(
                    crypto_ratio,
                    4
                ),

            "asset_types_count":
                len(asset_types),

            "portfolio_value":
                round(
                    total_portfolio,
                    2
                ),
        }
    }

    # =========================
    # CACHE STORE
    # =========================
    set_cache(
        cache_key,
        result,
        ttl=300
    )

    return result


TYPE_COPY = {
    "ai_rebalance": {
        "title": "Reequilibrer l'exposition dominante",
        "why": "La repartition actuelle montre une concentration qui peut amplifier les variations du patrimoine.",
        "impact": "Rendre le portefeuille plus lisible et reduire le risque de dependance a une seule classe d'actifs.",
        "action": "Verifier le poids cible de chaque classe d'actifs avant tout nouvel investissement.",
    },
    "business": {
        "title": "Tester un levier business simple",
        "why": "Le profil contient assez de base financiere pour tester un moteur de revenus sans complexifier tout le patrimoine.",
        "impact": "Creer une option de cashflow ou de valorisation future si le test trouve une traction reelle.",
        "action": "Definir une offre, un client cible et un test mesurable sur 7 a 14 jours.",
    },
    "commodities": {
        "title": "Ajouter une poche defensive",
        "why": "Ce signal sert surtout a etudier une diversification tangible, pas a rechercher un rendement rapide.",
        "impact": "Mieux equilibrer le portefeuille face aux cycles de marche et a l'inflation.",
        "action": "Comparer exposition directe, ETF et contraintes de liquidite avant decision.",
    },
    "crowdfunding": {
        "title": "Explorer un ticket fractionne",
        "why": "Le crowdfunding peut donner acces a des projets avec un ticket plus faible, mais le risque et la liquidite doivent etre lus avant rendement.",
        "impact": "Tester une exposition alternative sans immobiliser une part trop importante du patrimoine.",
        "action": "Comparer duree, garanties, historique de plateforme et scenario de perte avant tout ticket.",
    },
    "crypto": {
        "title": "Cadrer l'exposition crypto",
        "why": "Le profil accepte du risque, mais la crypto doit rester dimensionnee et suivie.",
        "impact": "Eviter que la performance depende d'une allocation trop volatile ou mal bornee.",
        "action": "Fixer un poids maximum, un rythme d'entree et une regle de reequilibrage.",
    },
    "diversification": {
        "title": "Reduire la concentration du portefeuille",
        "why": "Le nombre de classes d'actifs suivies est limite, ce qui peut rendre le patrimoine trop dependant d'un seul scenario.",
        "impact": "Ameliorer la resilience du patrimoine sans chercher plus de complexite.",
        "action": "Identifier la classe dominante et choisir une seule poche complementaire a analyser.",
    },
    "etf": {
        "title": "Construire un socle diversifie",
        "why": "Un ETF large peut servir de base simple quand l'objectif est de diversifier sans multiplier les lignes.",
        "impact": "Donner une exposition de long terme plus lisible et plus facile a piloter.",
        "action": "Verifier horizon, frais, devise, indice suivi et rythme d'investissement.",
    },
    "franchise": {
        "title": "Comparer un modele de franchise",
        "why": "La franchise est une piste business structuree, mais elle demande capital, temps et execution locale.",
        "impact": "Evaluer si un modele deja prouve peut etre plus pertinent qu'un business cree de zero.",
        "action": "Comparer ticket d'entree, royalties, zone de chalandise et temps d'exploitation requis.",
    },
    "private_equity": {
        "title": "Qualifier une opportunite privee",
        "why": "Ce type de piste n'est pertinent que si le capital, l'horizon et l'illiquidite sont compatibles.",
        "impact": "Acceder a une creation de valeur potentielle, avec un risque de liquidite plus eleve.",
        "action": "Verifier ticket minimum, duree de blocage, reporting et scenario de sortie.",
    },
    "real_estate": {
        "title": "Qualifier une piste immobiliere",
        "why": "La liquidite disponible peut justifier une analyse immobiliere, mais seulement si rendement, financement et charges restent coherents.",
        "impact": "Transformer une capacite patrimoniale en actif tangible sans fragiliser la reserve.",
        "action": "Simuler apport, mensualite, charges, vacance et rendement net avant visite ou engagement.",
    },
    "stocks": {
        "title": "Clarifier la strategie actions",
        "why": "Le signal actions doit servir a choisir une strategie lisible: revenus, croissance ou diversification passive.",
        "impact": "Eviter l'empilement de lignes et donner une logique au portefeuille cote.",
        "action": "Choisir une these principale et supprimer les lignes qui ne la servent pas.",
    },
    "startup": {
        "title": "Tester un MVP avant d'investir plus",
        "why": "Une opportunite startup n'a de sens que si elle valide un besoin concret avant de consommer du capital.",
        "impact": "Transformer une idee en preuve de demande, sans surexposer le patrimoine.",
        "action": "Definir le probleme, une promesse, un prototype et un critere de validation client.",
    },
}


def _normalize_text(value):
    return str(value or "").strip()


def enrich_opportunity(raw: dict, profile: dict | None = None, source: str = "module") -> dict:
    profile = profile or {}
    raw = raw or {}
    opp_type = _normalize_text(raw.get("type") or "opportunity").lower()
    copy = TYPE_COPY.get(opp_type, {})
    risk = _normalize_text(raw.get("risk"))
    potential = _normalize_text(raw.get("potential"))
    budget = _normalize_text(raw.get("budget"))
    difficulty = _normalize_text(raw.get("difficulty"))
    title = _normalize_text(raw.get("title") or copy.get("title") or "Opportunite a qualifier")
    score = safe_float(raw.get("score"))

    if score <= 0:
        score = 55
        if potential in ["high", "very_high"]:
            score += 12
        if risk == "high":
            score -= 8
        if difficulty in ["advanced", "high"]:
            score -= 6
        if budget == "low":
            score += 4
        score = max(35, min(90, round(score)))

    priority = raw.get("priority")
    if not priority:
        priority = "high" if score >= 85 else "medium" if score >= 60 else "low"

    description = _normalize_text(raw.get("description") or copy.get("why"))
    impact = _normalize_text(raw.get("impact_potential") or copy.get("impact"))
    action = _normalize_text(raw.get("next_action") or copy.get("action"))
    why = _normalize_text(raw.get("why_this_opportunity") or copy.get("why") or description)

    return {
        **raw,
        "type": opp_type,
        "title": title,
        "description": description,
        "priority": priority,
        "score": score,
        "premium": bool(raw.get("premium", False)),
        "why_this_opportunity": why,
        "impact_potential": impact,
        "next_action": action,
        "difficulty": difficulty or raw.get("profile_compatibility"),
        "risk": risk or raw.get("risk"),
        "budget": budget or raw.get("budget"),
        "potential": potential or raw.get("potential"),
        "source": source,
    }


def merge_opportunity_sets(profile: dict, portfolio: list, module_opportunities: list | None = None):
    contextual = compute_opportunities(profile, portfolio).get("opportunities", [])
    module_opportunities = module_opportunities or []
    merged = {}

    for raw in contextual:
        enriched = enrich_opportunity(raw, profile, "profile")
        merged[enriched["type"]] = enriched

    for raw in module_opportunities:
        enriched = enrich_opportunity(raw, profile, "module")
        current = merged.get(enriched["type"])
        if current and safe_float(current.get("score")) >= safe_float(enriched.get("score")):
            continue
        merged[enriched["type"]] = enriched

    opportunities = sorted(
        merged.values(),
        key=lambda item: safe_float(item.get("score")),
        reverse=True,
    )[:12]

    return {
        "count": len(opportunities),
        "opportunities": opportunities,
        "analytics": {
            "source": "profile_and_module_merge",
            "contextual_count": len(contextual),
            "module_count": len(module_opportunities),
        },
    }
