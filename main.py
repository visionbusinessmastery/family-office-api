from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
import os

# ======================
# CONFIG
# ======================

api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

app = FastAPI(
    title="Family Office IA API",
    version="0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# STOCKAGE MVP
# ======================

user_profile = {}

# ======================
# MODELS
# ======================

class IARequest(BaseModel):
    message: str


class ProfileRequest(BaseModel):

    revenus: float
    charges: float

    epargne: float
    immobilier: float
    investissements: float
    crypto: float

    objectif: str
    horizon: int
    risque: str

    age: int
    pays: str
    experience: str


# ======================
# ROUTE TEST
# ======================

@app.get("/")
def root():
    return {"status": "Family Office IA API running"}


# ======================
# PROFIL UTILISATEUR
# ======================

@app.post("/profile")
def save_profile(profile: ProfileRequest):

    global user_profile
    user_profile = profile.dict()

    capacite = profile.revenus - profile.charges

    patrimoine_total = (
        profile.epargne +
        profile.immobilier +
        profile.investissements +
        profile.crypto
    )

    diagnostic = f"""
📊 DIAGNOSTIC FINANCIER

Revenus : {profile.revenus} €
Charges : {profile.charges} €
Capacité d'investissement : {capacite} €

Patrimoine total : {patrimoine_total} €

Profil de risque : {profile.risque}
Horizon : {profile.horizon} ans
"""

    return {
        "status": "ok",
        "message": "Profil enregistré",
        "diagnostic": diagnostic
    }


# ======================
# COACH IA
# ======================

@app.post("/ia/analyse")
def ia_analyse(request: IARequest):

    if not user_profile:
        return {
            "diagnostic": "Profil utilisateur non renseigné",
            "axes": ["Merci de compléter votre profil financier"],
            "plan_action": ["Renseigner revenus, charges et objectifs"],
            "note": "Profil requis pour analyse personnalisée"
        }

    revenus = user_profile["revenus"]
    charges = user_profile["charges"]
    objectif = user_profile["objectif"]
    horizon = user_profile["horizon"]
    risque = user_profile["risque"]

    reste = revenus - charges

    diagnostic = (
        f"Revenus mensuels : {revenus} €\n"
        f"Charges mensuelles : {charges} €\n"
        f"Capacité mensuelle : {reste} €\n"
        f"Horizon : {horizon} ans\n"
        f"Profil de risque : {risque}"
    )

    axes = []

    if reste <= 0:
        axes.append("Optimisation budgétaire prioritaire")
    else:
        axes.append("Capacité d’investissement détectée")

    axes.append(f"Objectif principal : {objectif}")

    plan_action = [
        "Construire une épargne de sécurité (3 à 6 mois de charges)",
        "Mettre en place une stratégie d'investissement progressive",
        "Diversifier entre actions, immobilier et actifs alternatifs"
    ]

    return {
        "diagnostic": diagnostic,
        "axes": axes,
        "plan_action": plan_action,
        "note": "Analyse IA – aide à la décision"
    }


# ======================
# ANALYSE ACTION
# ======================

@app.post("/stocks/analyse")
def analyse_action(data: dict):

    ticker = data.get("ticker")

    if not ticker:
        return {"error": "Ticker manquant"}

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    if not api_key:
        return {"error": "Clé API manquante"}

    try:

        url = (
            "https://www.alphavantage.co/query"
            f"?function=GLOBAL_QUOTE"
            f"&symbol={ticker.upper()}"
            f"&apikey={api_key}"
        )

        r = requests.get(url)
        data_json = r.json()

        quote = data_json.get("Global Quote", {})

        if not quote:
            return {"error": "Action introuvable"}

        return {
            "ticker": ticker.upper(),
            "prix": quote.get("05. price"),
            "variation": quote.get("10. change percent"),
            "analyse": "Données récupérées via Alpha Vantage",
            "forces": ["Données temps réel"],
            "risques": ["Limite de requêtes API"],
            "strategie": "Analyse à enrichir avec indicateurs techniques"
        }

    except:
        return {"error": "Erreur serveur"}

# ======================
# STOCK PICKER
# ======================

@app.get("/stockpicker")
def stock_picker():

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    if not api_key:
        return {"stocks": []}

    # Liste d'actions à surveiller
    symbols = ["TSLA", "AAPL", "MSFT", "NVDA", "GOOGL"]

    stocks = []

    for symbol in symbols:

        try:

            url = (
                "https://www.alphavantage.co/query"
                f"?function=GLOBAL_QUOTE"
                f"&symbol={symbol}"
                f"&apikey={api_key}"
            )

            r = requests.get(url)
            data = r.json()

            quote = data.get("Global Quote", {})

            if quote:

                stocks.append({
                    "symbol": quote.get("01. symbol"),
                    "price": quote.get("05. price"),
                    "change": quote.get("10. change percent")
                })

        except:
            continue

    return {"stocks": stocks}

# ======================
# IMMOBILIER
# ======================

@app.get("/realestate/opportunities")
def realestate_opportunities():

    opportunities = [

        {"ville": "Lisbonne", "rendement": "6.5%"},
        {"ville": "Dubaï", "rendement": "7.2%"},
        {"ville": "Athènes", "rendement": "6%"}

    ]

    return {"real_estate": opportunities}


# ======================
# IDEES BUSINESS
# ======================

@app.get("/business/ideas")
def business_ideas():

    ideas = [

        {"idea": "Agence IA pour PME"},
        {"idea": "Location courte durée automatisée"},
        {"idea": "Newsletter premium marchés financiers"}

    ]

    return {"business_ideas": ideas}


# ======================
# TENDANCES
# ======================

@app.get("/market/trends")
def market_trends():

    trends = {

        "secteurs_croissance": [
            "Intelligence artificielle",
            "Cyber sécurité",
            "Semi-conducteurs",
            "Energies renouvelables"
        ],

        "secteurs_declins": [
            "Retail physique",
            "Presse papier"
        ],

        "secteurs_emergents": [
            "Spatial",
            "Biotech longévité",
            "Robotique"
        ]

    }

    return trends





