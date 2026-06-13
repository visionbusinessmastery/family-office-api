from fastapi import APIRouter, Depends

from auth.utils import get_current_user
from intelligence.affiliate_registry import AFFILIATE_ENGINES


router = APIRouter()


CATEGORY_COPY = {
    "ai_business": {
        "label": "Business IA",
        "description": "Outils utiles pour prototyper, automatiser ou structurer une activite digitale.",
    },
    "banking": {
        "label": "Banque",
        "description": "Services utiles pour comptes, paiements, devises ou pilotage du cash.",
    },
    "business": {
        "label": "Business",
        "description": "Outils pour vendre, lancer une offre ou structurer un canal de revenus.",
    },
    "commodities": {
        "label": "Matieres premieres",
        "description": "Solutions liees a l'or, aux metaux ou a une poche de diversification tangible.",
    },
    "crowdfunding": {
        "label": "Crowdfunding",
        "description": "Plateformes pour explorer des tickets fractionnes ou du financement participatif.",
    },
    "crypto": {
        "label": "Crypto",
        "description": "Plateforme utile pour acceder aux actifs crypto avec une logique de risque encadree.",
    },
    "etf": {
        "label": "ETF",
        "description": "Solution utile pour une allocation simple, diversifiee et suivie dans le temps.",
    },
    "franchise": {
        "label": "Franchise",
        "description": "Source pour explorer des concepts de franchise et comparer des modeles existants.",
    },
    "market": {
        "label": "Marches",
        "description": "Outils de suivi marche pour lire tendances, graphiques et donnees macro.",
    },
    "private_equity": {
        "label": "Private equity",
        "description": "Outils utiles pour structurer, suivre ou professionnaliser une activite privee.",
    },
    "real_estate": {
        "label": "Immobilier",
        "description": "Plateformes pour explorer une exposition immobiliere ou des actifs fractionnes.",
    },
    "startup": {
        "label": "Startup",
        "description": "Outils pour encaisser, lancer ou tester rapidement une activite en ligne.",
    },
    "stocks": {
        "label": "Actions",
        "description": "Plateformes ou outils utiles pour investir, comparer ou suivre les marches.",
    },
    "trading": {
        "label": "Trading",
        "description": "Outils avances pour analyser les marches, suivre des signaux et executer avec discipline.",
    },
}


PARTNER_COPY = {
    "Axonaut": "Suite de gestion pour structurer une activite, suivre clients, ventes et pilotage commercial.",
    "Binance": "Plateforme crypto pour acheter, vendre ou suivre des actifs numeriques avec une logique de risque.",
    "Bricks": "Plateforme orientee immobilier fractionne ou financement participatif selon les offres disponibles.",
    "BullionVault": "Service specialise dans l'achat et la garde de metaux precieux.",
    "Degiro": "Courtier en ligne pour acceder a des actions, ETF et marches financiers.",
    "eToro": "Plateforme d'investissement grand public pour explorer differents actifs financiers.",
    "Fundora": "Plateforme de financement participatif pour explorer des opportunites de rendement.",
    "GoldBroker": "Service specialise dans l'achat et la conservation d'or et metaux precieux.",
    "Interactive Brokers": "Courtier avance pour investisseurs actifs, multi-marches et multi-devises.",
    "Investing.com Pro": "Outil de suivi marche, donnees financieres et lecture d'actifs cotes.",
    "MacroTrends": "Source de donnees historiques et macro pour remettre les chiffres dans le temps long.",
    "Make": "Outil d'automatisation pour connecter des applications et reduire les operations manuelles.",
    "N26": "Banque mobile utile pour separer, suivre ou simplifier certains flux financiers.",
    "Notion": "Espace de travail pour organiser projets, process, notes et pilotage operationnel.",
    "OpenAI": "Plateforme IA pour prototyper des assistants, automatisations ou produits digitaux.",
    "RealT": "Plateforme d'exposition immobiliere tokenisee, a analyser avec prudence cote risque et liquidite.",
    "Revolut": "Compte multi-devises utile pour paiements, devises et separation de flux.",
    "Shopify": "Plateforme e-commerce pour lancer une boutique, tester une offre ou structurer une vente en ligne.",
    "Stripe": "Infrastructure de paiement pour encaisser en ligne et professionnaliser un business digital.",
    "Systeme.io": "Plateforme pour tunnels de vente, email marketing et lancement d'offres digitales.",
    "Toute La Franchise": "Annuaire et source d'information pour explorer des reseaux de franchise.",
    "Trade Republic": "Plateforme d'investissement orientee actions, ETF et gestion simple d'un portefeuille.",
    "TradingView": "Outil de graphiques, alertes et suivi marche pour analyser les actifs financiers.",
    "Wise": "Service multi-devises utile pour transferts, conversions et paiements internationaux.",
}


def normalize_affiliate(raw: dict, source_key: str, index: int) -> dict:
    name = str(raw.get("name") or "Partenaire").strip()
    category = str(raw.get("category") or source_key).strip()
    category_copy = CATEGORY_COPY.get(category, CATEGORY_COPY.get(source_key, {}))
    description = raw.get("description") or PARTNER_COPY.get(name) or category_copy.get("description")

    return {
        "id": f"{category}:{name.lower().replace(' ', '-')}",
        "name": name,
        "category": category,
        "category_label": category_copy.get("label") or category.replace("_", " ").title(),
        "description": description,
        "benefit": raw.get("benefit") or category_copy.get("description"),
        "url": raw.get("url"),
        "source": source_key,
        "rank": index,
    }


@router.get("/affiliates")
def get_affiliates(user=Depends(get_current_user)):
    partners = []
    seen = set()

    for source_key, engine in AFFILIATE_ENGINES.items():
        try:
            items = engine() or []
        except Exception:
            items = []

        for index, item in enumerate(items):
            normalized = normalize_affiliate(item, source_key, index)
            unique_key = (normalized.get("name"), normalized.get("url"))
            if unique_key in seen:
                continue
            seen.add(unique_key)
            partners.append(normalized)

    partners.sort(key=lambda item: (item.get("category_label") or "", item.get("name") or ""))

    return {
        "count": len(partners),
        "partners": partners,
        "source": "affiliate_registry",
        "sync": "Les changements dans les affiliate_engine du registre sont renvoyes au prochain chargement front.",
    }
