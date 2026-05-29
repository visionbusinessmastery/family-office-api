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


PLAN_MIN_OPPORTUNITIES = {
    "FREE": 3,
    "GOLD": 6,
    "ELITE": 8,
    "LIBERTY": 10,
    "LEGACY": 20,
}


def opportunity_limit_for_plan(plan: str) -> int:
    normalized = normalize_plan(plan)
    if plan_allows(normalized, "LEGACY"):
        return 20
    if plan_allows(normalized, "LIBERTY"):
        return 15
    if plan_allows(normalized, "GOLD"):
        return 8
    return 3


def context_summary(profile):
    goals = profile.get("goals") or []
    motivation = profile.get("motivation")
    professional = profile.get("professional_context") or profile.get("investor_profile")
    has_children = bool(profile.get("has_children"))
    expertise = profile.get("expertise")

    return {
        "goals": goals,
        "motivation": motivation,
        "professional": professional,
        "has_children": has_children,
        "expertise": expertise or (
            "marketing" if "marketing" in str(professional or "").lower() else None
        ),
        "wants_income": any("revenu" in str(item).lower() for item in goals)
        or "revenu" in str(motivation or "").lower()
        or "liberte" in str(motivation or "").lower(),
    }


def enrich_opportunity(item, profile, defaults=None):
    defaults = defaults or {}
    context = context_summary(profile)
    compatibility_bits = []
    if context["has_children"]:
        compatibility_bits.append("charge familiale")
    if context["expertise"]:
        compatibility_bits.append(f"expertise {context['expertise']}")
    if context["wants_income"]:
        compatibility_bits.append("objectif revenus")

    return {
        "why_this_opportunity": defaults.get("why") or item.get("why_this_opportunity") or "Elle repond a un levier visible dans ton profil actuel.",
        "why_now": defaults.get("why_now") or item.get("why_now") or "Le cockpit contient assez de signaux pour qualifier une prochaine action sans multiplier les pistes.",
        "impact_potential": defaults.get("impact") or item.get("impact_potential") or "Impact potentiel modere, a valider avec une action simple.",
        "difficulty": defaults.get("difficulty") or item.get("difficulty") or "moyenne",
        "profile_compatibility": defaults.get("compatibility") or item.get("profile_compatibility") or (
            ", ".join(compatibility_bits) if compatibility_bits else "compatibilite a confirmer avec tes contraintes de temps"
        ),
        "next_action": defaults.get("next_action") or item.get("next_action") or "Choisir une micro-action executable cette semaine.",
        **item,
    }


def ensure_plan_opportunity_depth(opportunities, profile, analytics=None):
    plan = normalize_plan(profile.get("plan"))
    target = PLAN_MIN_OPPORTUNITIES.get(plan, 3)
    limit = opportunity_limit_for_plan(plan)
    analytics = analytics or {}
    existing_types = {
        str(item.get("type") or item.get("title") or "").lower()
        for item in opportunities
        if isinstance(item, dict)
    }

    total_portfolio = safe_float(analytics.get("portfolio_value") or profile.get("portfolio_value"))
    savings = safe_float(profile.get("savings"))
    monthly_income = safe_float(profile.get("monthly_income"))
    risk = (profile.get("risk_profile") or "medium").lower()
    context = context_summary(profile)

    candidates = [
        {
            "type": "cash_reserve",
            "title": "Reserve de securite",
            "description": "Verifier que la tresorerie couvre les charges avant d'augmenter le risque.",
            "priority": "high" if savings < max(3000, monthly_income) else "medium",
            "score": 82,
            "premium": False,
            "why_this_opportunity": "Avant d'ajouter du risque, le backend verifie si la base de securite protege la vie quotidienne.",
            "why_now": "La reserve conditionne la serenite des prochaines decisions.",
            "impact_potential": "Stabilite et baisse de stress financier.",
            "difficulty": "faible",
            "profile_compatibility": "utile si charges familiales ou revenus actifs",
            "next_action": "Calculer 3 mois de charges et isoler le manque exact.",
        },
        {
            "type": "etf_core",
            "title": "Socle ETF diversifie",
            "description": "Construire une poche simple et liquide si le portefeuille manque de base long terme.",
            "priority": "medium",
            "score": 78,
            "premium": False,
            "why_this_opportunity": "Un socle liquide evite que chaque decision depende d'une opportunite isolee.",
            "why_now": "Le portefeuille a besoin d'une base simple avant les arbitrages plus fins.",
            "impact_potential": "Diversification progressive et lisibilite long terme.",
            "difficulty": "faible",
            "profile_compatibility": "compatible avec peu de temps disponible",
            "next_action": "Choisir une enveloppe et definir un montant test mensuel.",
        },
        {
            "type": "income_tracking",
            "title": "Suivi revenus recurrents",
            "description": "Relier chaque allocation a son impact cashflow ou a son horizon de valorisation.",
            "priority": "medium",
            "score": 74,
            "premium": False,
            "why_this_opportunity": "Chaque actif doit etre relie a un role concret: revenu, protection ou valorisation.",
            "why_now": "Le backend detecte un besoin de relier allocation et trajectoire de vie.",
            "impact_potential": "Meilleure coherence entre revenus actifs, epargne et investissement.",
            "difficulty": "moyenne",
            "profile_compatibility": "adaptable a tes revenus actuels",
            "next_action": "Associer chaque ligne a un role en une phrase.",
        },
        {
            "type": "risk_budget",
            "title": "Budget de risque par poche",
            "description": "Fixer une limite par classe d'actifs avant toute nouvelle opportunite.",
            "priority": "high" if risk == "high" else "medium",
            "score": 80,
            "premium": plan_allows(plan, "GOLD"),
            "why_this_opportunity": "Le budget de risque empeche une opportunite attirante de devenir une charge mentale.",
            "why_now": "Le portefeuille commence a avoir assez de donnees pour fixer des limites.",
            "impact_potential": "Moins de dispersion et meilleure discipline.",
            "difficulty": "moyenne",
            "profile_compatibility": "utile si temps limite ou famille a proteger",
            "next_action": "Fixer un plafond par classe d'actifs avant le prochain achat.",
        },
        {
            "type": "real_estate_screening",
            "title": "Screening immobilier net",
            "description": "Comparer rendement net, vacance, charges et revente avant d'ajouter un bien.",
            "priority": "medium",
            "score": 76,
            "premium": plan_allows(plan, "GOLD"),
            "why_this_opportunity": "L'immobilier n'est pertinent que si le net-net respecte la tresorerie et le temps disponible.",
            "why_now": "Une analyse froide evite de confondre rendement affiche et vraie robustesse.",
            "impact_potential": "Stabilite patrimoniale si le cashflow reste prudent.",
            "difficulty": "elevee",
            "profile_compatibility": "a filtrer selon charge familiale et disponibilite",
            "next_action": "Comparer deux biens avec charges, vacance et travaux inclus.",
        },
        {
            "type": "business_cashflow",
            "title": "Revenus complementaires",
            "description": "Tester une piste business avec faible capital et validation terrain rapide.",
            "priority": "medium",
            "score": 73,
            "premium": plan_allows(plan, "GOLD"),
            "why_this_opportunity": "Augmenter les revenus peut etre plus puissant qu'optimiser trop tot l'allocation.",
            "why_now": "Le profil indique un besoin de levier revenu avant de complexifier le patrimoine.",
            "impact_potential": "Hausse de capacite d'epargne et d'investissement.",
            "difficulty": "moyenne",
            "profile_compatibility": "compatible si l'offre reste simple et peu chronophage",
            "next_action": "Identifier une offre courte que tu peux vendre sans nouvelle infrastructure.",
        },
        {
            "type": "currency_exposure",
            "title": "Exposition devises",
            "description": "Identifier si une devise concentre trop le patrimoine ou les revenus futurs.",
            "priority": "low",
            "score": 68,
            "premium": plan_allows(plan, "LIBERTY"),
            "why_this_opportunity": "Les devises peuvent proteger ou fragiliser selon revenus, actifs et projets futurs.",
            "why_now": "La lecture multi-actifs devient utile a partir d'un patrimoine plus structure.",
            "impact_potential": "Meilleure protection contre une concentration invisible.",
            "difficulty": "moyenne",
            "profile_compatibility": "utile si revenus, projets ou patrimoine hors devise principale",
            "next_action": "Lister devise des revenus, charges et principaux actifs.",
        },
        {
            "type": "scenario_12m",
            "title": "Scenario 12 mois",
            "description": "Projeter cashflow, nouveaux apports et arbitrages probables sur un an.",
            "priority": "medium",
            "score": 79,
            "premium": plan_allows(plan, "LIBERTY"),
            "why_this_opportunity": "Un scenario force les arbitrages: temps, cashflow, risque et objectifs.",
            "why_now": "Le niveau Liberty justifie une lecture plus prospective.",
            "impact_potential": "Decisions plus calmes sur 12 mois.",
            "difficulty": "moyenne",
            "profile_compatibility": "tres utile avec objectifs revenus ou famille",
            "next_action": "Construire trois lignes: revenu attendu, epargne cible, allocation probable.",
        },
        {
            "type": "family_governance",
            "title": "Gouvernance familiale",
            "description": "Clarifier roles, documents et objectifs de transmission a long terme.",
            "priority": "medium",
            "score": 77,
            "premium": plan_allows(plan, "LEGACY"),
            "why_this_opportunity": "Le patrimoine familial demande des roles, pas seulement des actifs.",
            "why_now": "Legacy sert a rendre la trajectoire transmissible et moins dependante d'une seule personne.",
            "impact_potential": "Clarification familiale et reduction du risque de transmission.",
            "difficulty": "elevee",
            "profile_compatibility": "forte si enfants, heritiers ou gouvernance familiale",
            "next_action": "Ecrire les trois decisions familiales qui doivent etre documentees.",
        },
        {
            "type": "liquidity_ladder",
            "title": "Echelle de liquidite",
            "description": "Organiser cash disponible, epargne de securite et capital long terme en poches lisibles.",
            "priority": "medium",
            "score": 75,
            "premium": plan_allows(plan, "GOLD"),
            "why_this_opportunity": "Elle reduit la confusion entre argent disponible et capital vraiment investissable.",
            "why_now": "La prochaine allocation doit respecter le quotidien avant la performance.",
            "impact_potential": "Moins d'arbitrages impulsifs et meilleure serenite.",
            "difficulty": "faible",
            "profile_compatibility": "compatible avec temps limite",
            "next_action": "Nommer trois poches: securite, projets 12 mois, long terme.",
        },
        {
            "type": "recurring_offer",
            "title": "Offre recurrente faible charge mentale",
            "description": "Transformer une competence en revenu recurrent simple a livrer.",
            "priority": "high" if context["wants_income"] else "medium",
            "score": 84,
            "premium": plan_allows(plan, "GOLD"),
            "why_this_opportunity": "Un revenu recurrent augmente la capacite d'investissement sans dependre uniquement du salaire.",
            "why_now": "Le levier revenu peut preceder une diversification plus ambitieuse.",
            "impact_potential": "Cashflow additionnel et meilleure marge de manoeuvre.",
            "difficulty": "moyenne",
            "profile_compatibility": "forte si competence exploitable ou business existant",
            "next_action": "Lister une offre livrable en moins de 2 heures par client.",
        },
        {
            "type": "portfolio_roles",
            "title": "Role de chaque actif",
            "description": "Classer chaque ligne comme protection, revenu, croissance ou option strategique.",
            "priority": "medium",
            "score": 72,
            "premium": plan_allows(plan, "GOLD"),
            "why_this_opportunity": "Un portefeuille premium n'est pas une accumulation de lignes: chaque actif doit avoir une fonction.",
            "why_now": "Cela evite d'acheter une opportunite qui double un risque deja present.",
            "impact_potential": "Meilleure coherence d'allocation.",
            "difficulty": "faible",
            "profile_compatibility": "utile quel que soit le niveau de patrimoine",
            "next_action": "Ajouter un role en un mot a chaque actif suivi.",
        },
        {
            "type": "debt_review",
            "title": "Audit dette et charges fixes",
            "description": "Verifier si une charge ou une dette limite le levier revenu/investissement.",
            "priority": "medium",
            "score": 70,
            "premium": plan_allows(plan, "GOLD"),
            "why_this_opportunity": "Liberer une charge fixe peut produire un effet equivalent a un nouveau revenu.",
            "why_now": "Les arbitrages deviennent plus puissants quand la base mensuelle est allegee.",
            "impact_potential": "Cashflow disponible et baisse du stress.",
            "difficulty": "moyenne",
            "profile_compatibility": "utile si revenus actifs ou famille a charge",
            "next_action": "Identifier la charge fixe la plus lourde et son option d'optimisation.",
        },
        {
            "type": "education_goal",
            "title": "Objectif education enfant",
            "description": "Creer une enveloppe enfant avec objectif, horizon et contribution mensuelle.",
            "priority": "medium",
            "score": 78,
            "premium": plan_allows(plan, "LIBERTY"),
            "why_this_opportunity": "Elle transforme la transmission en action concrete et mesurable.",
            "why_now": "Le module comptes enfants rend ce suivi directement pilotable.",
            "impact_potential": "Preparation familiale visible et progressive.",
            "difficulty": "faible",
            "profile_compatibility": "forte si enfants ou heritiers",
            "next_action": "Creer un compte enfant avec un montant cible et une contribution mensuelle.",
        },
        {
            "type": "automation_income",
            "title": "Automatisation d'un revenu existant",
            "description": "Automatiser une partie acquisition, livraison ou suivi client d'une activite existante.",
            "priority": "medium",
            "score": 82,
            "premium": plan_allows(plan, "LIBERTY"),
            "why_this_opportunity": "Le temps est souvent la contrainte centrale; automatiser protege l'energie.",
            "why_now": "Liberty sert a arbitrer business, cashflow et patrimoine ensemble.",
            "impact_potential": "Plus de revenu par heure disponible.",
            "difficulty": "moyenne",
            "profile_compatibility": "forte avec business ou expertise marketing",
            "next_action": "Choisir une tache repetee et definir une automatisation simple.",
        },
        {
            "type": "family_document_vault",
            "title": "Inventaire documents familiaux",
            "description": "Lister contrats, comptes, assurances, documents patrimoniaux et acces critiques.",
            "priority": "medium",
            "score": 79,
            "premium": plan_allows(plan, "LEGACY"),
            "why_this_opportunity": "La protection familiale commence par la lisibilite des informations essentielles.",
            "why_now": "Legacy doit reduire la dependance a une seule personne.",
            "impact_potential": "Continuite familiale et baisse du risque operationnel.",
            "difficulty": "moyenne",
            "profile_compatibility": "forte en strategie familiale",
            "next_action": "Lister les 10 documents ou acces les plus importants.",
        },
        {
            "type": "succession_note",
            "title": "Note de transmission",
            "description": "Rediger une premiere note expliquant intentions, priorites et personnes de confiance.",
            "priority": "medium",
            "score": 76,
            "premium": plan_allows(plan, "LEGACY"),
            "why_this_opportunity": "Une intention claire evite que le patrimoine devienne opaque pour les proches.",
            "why_now": "La strategie generationnelle doit etre explicite avant les optimisations complexes.",
            "impact_potential": "Meilleure preparation familiale.",
            "difficulty": "faible",
            "profile_compatibility": "forte si enfants, heritiers ou patrimoine familial",
            "next_action": "Ecrire une page: ce qui compte, qui appeler, quoi proteger.",
        },
        {
            "type": "governance_calendar",
            "title": "Calendrier de gouvernance",
            "description": "Installer un rendez-vous trimestriel pour revoir patrimoine, objectifs et risques.",
            "priority": "low",
            "score": 71,
            "premium": plan_allows(plan, "LEGACY"),
            "why_this_opportunity": "Un Family Office avance vit par cadence, pas par impulsion.",
            "why_now": "La progression doit devenir un rituel de decision.",
            "impact_potential": "Discipline et transmission plus fluide.",
            "difficulty": "faible",
            "profile_compatibility": "forte pour famille ou multi-actifs",
            "next_action": "Bloquer un rendez-vous trimestriel de 45 minutes.",
        },
        {
            "type": "protection_review",
            "title": "Revue protection familiale",
            "description": "Verifier assurances, dependance aux revenus actifs et scenarios d'interruption.",
            "priority": "medium",
            "score": 74,
            "premium": plan_allows(plan, "LEGACY"),
            "why_this_opportunity": "La protection est le socle invisible d'une architecture patrimoniale durable.",
            "why_now": "Plus le patrimoine grandit, plus l'interruption de revenus ou de gouvernance coute cher.",
            "impact_potential": "Reduction des risques de rupture familiale et financiere.",
            "difficulty": "moyenne",
            "profile_compatibility": "forte si enfants ou revenus actifs dominants",
            "next_action": "Lister trois scenarios a couvrir: sante, revenus, transmission.",
        },
        {
            "type": "family_education",
            "title": "Education financiere familiale",
            "description": "Transformer une notion patrimoniale en rituel simple pour les enfants ou heritiers.",
            "priority": "low",
            "score": 69,
            "premium": plan_allows(plan, "LEGACY"),
            "why_this_opportunity": "Un patrimoine transmis sans culture financiere reste fragile.",
            "why_now": "La valeur Legacy vient aussi de la competence transmise, pas seulement des actifs.",
            "impact_potential": "Meilleure continuite generationnelle.",
            "difficulty": "faible",
            "profile_compatibility": "forte pour logique familiale",
            "next_action": "Choisir une notion simple a expliquer ce mois-ci: epargne, risque ou revenu.",
        },
    ]

    if context["expertise"] and context["wants_income"]:
        candidates.insert(0, {
            "type": "expertise_monetization",
            "title": f"Offre premium basee sur ton expertise {context['expertise']}",
            "description": "Transformer une competence existante en offre courte, recurrente ou semi-automatisee.",
            "priority": "high",
            "score": 88,
            "premium": plan_allows(plan, "GOLD"),
            "why_this_opportunity": "Elle part de ce que tu sais deja faire, donc elle limite le risque d'apprentissage et la charge mentale.",
            "why_now": "Ton objectif revenu est mieux servi par un levier actif scalable que par une micro-optimisation patrimoniale.",
            "impact_potential": "Augmenter la capacite d'epargne sans ajouter un projet lourd.",
            "difficulty": "moyenne",
            "profile_compatibility": "forte si temps limite, enfants ou activite existante",
            "next_action": "Rediger une offre en une phrase et contacter 3 prospects proches.",
        })

    if total_portfolio >= 100000:
        candidates.append({
            "type": "private_markets",
            "title": "Poche non cotee controlee",
            "description": "Etudier une allocation privee seulement si liquidite et horizon sont compatibles.",
            "priority": "medium",
            "score": 81,
            "premium": plan_allows(plan, "LIBERTY"),
        })

    for candidate in candidates:
        if len(opportunities) >= target or len(opportunities) >= limit:
            break
        key = str(candidate["type"]).lower()
        if key in existing_types:
            continue
        opportunities.append(candidate)
        existing_types.add(key)

    return opportunities[:limit]


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
                    "Reequilibrage data-only",

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
    opportunities = [
        enrich_opportunity(item, profile)
        for item in ensure_plan_opportunity_depth(
            opportunities,
            profile,
            {
                "crypto_ratio": crypto_ratio,
                "asset_types_count": len(asset_types),
                "portfolio_value": total_portfolio,
            },
        )
    ]

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
