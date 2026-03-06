from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
import os

# ======================
# CONFIG
# ======================

FMP_API_KEY = os.getenv("FMP_API_KEY")

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

    url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={FMP_API_KEY}"

    r = requests.get(url).json()

    if not r:
        return {"error": "Action introuvable"}

    stock = r[0]

    return {
        "ticker": ticker.upper(),
        "entreprise": stock["companyName"],
        "secteur": stock["sector"],
        "prix": stock["price"],
        "description": stock["description"]
    }


# ======================
# STOCK PICKER
# ======================

@app.get("/stockpicker")
def stock_picker():

    if not FMP_API_KEY:
        return {"stocks": []}

    symbols = [
        "AAPL","MSFT","NVDA","GOOGL","AMZN",
        "TSLA","META","V","ASML","LVMH"
    ]

    stocks = []

    for symbol in symbols:

        url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={FMP_API_KEY}"

        r = requests.get(url).json()

        if r:
            stock = r[0]

            stocks.append({
                "symbol": stock["symbol"],
                "price": stock["price"],
                "change": stock["changesPercentage"]
            })

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
