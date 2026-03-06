from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
import os
import requests

# ======================
# CONFIGURATION API
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
# SCHEDULER
# ======================

scheduler = BackgroundScheduler()

def daily_scan():
    print("Scan quotidien des opportunités...")

scheduler.add_job(daily_scan, "interval", hours=24)
scheduler.start()

# ======================
# MODELS
# ======================

class IARequest(BaseModel):
    message: str


class ProfileRequest(BaseModel):

    # Revenus
    revenus: float
    charges: float

    # Patrimoine
    epargne: float
    immobilier: float
    investissements: float
    crypto: float

    # Objectifs
    objectif: str
    horizon: int
    risque: str

    # Infos utilisateur
    age: int
    pays: str
    experience: str


# ======================
# STOCKAGE PROFIL (MVP)
# ======================

user_profile = {}

# ======================
# ROUTE TEST
# ======================

@app.get("/")
def root():
    return {"status": "Family Office IA API running"}

# ======================
# ENREGISTREMENT PROFIL
# ======================

@app.post("/profile")
def save_profile(profile: ProfileRequest):

    global user_profile
    user_profile = profile.dict()

    capacite = profile.revenus - profile.charges

    patrimoine_total = (
        profile.epargne
        + profile.immobilier
        + profile.investissements
        + profile.crypto
    )

    return {
        "status": "ok",
        "message": "Profil enregistré avec succès",

        "diagnostic": f"""
📊 DIAGNOSTIC FINANCIER

Revenus : {profile.revenus} €
Charges : {profile.charges} €
Capacité d'investissement : {capacite} €

Patrimoine total : {patrimoine_total} €

Profil : {profile.risque}
Horizon : {profile.horizon} ans
        """
    }

# ======================
# COACH PATRIMONIAL IA
# ======================

@app.post("/ia/analyse")
def ia_analyse(request: IARequest):

    if not user_profile:
        return {
            "diagnostic": "Profil utilisateur non renseigné",
            "axes": ["Merci de compléter votre profil financier"],
            "plan_action": ["Renseigner revenus, charges, objectifs"],
            "note": "Profil requis pour une analyse personnalisée"
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
    elif reste < revenus * 0.2:
        axes.append("Capacité d'investissement modérée")
    else:
        axes.append("Excellente capacité d'investissement")

    axes.append(f"Objectif principal : {objectif}")

    plan_action = [
        "Construire une épargne de sécurité (3 à 6 mois de charges)",
        "Investir progressivement selon le profil de risque",
        "Diversifier entre actions, immobilier et actifs alternatifs"
    ]

    return {
        "diagnostic": diagnostic,
        "axes": axes,
        "plan_action": plan_action,
        "note": "Analyse IA – aide à la décision uniquement"
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

        "score": 7,

        "analyse": f"{stock['companyName']} opère dans le secteur {stock['sector']}. Entreprise solide avec potentiel long terme.",

        "forces": [
            "Position de marché solide",
            "Secteur porteur",
            "Potentiel de croissance"
        ],

        "risques": [
            "Volatilité du marché",
            "Concurrence technologique"
        ],

        "strategie": "Accumulation progressive long terme"
    }

# ======================
# STOCK PICKER IA
# ======================

@app.get("/stockpicker")
def stock_picker():

    if not FMP_API_KEY:
        return {"result": "Clé API manquante"}

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
# OPPORTUNITES IMMOBILIER
# ======================

@app.get("/realestate/opportunities")
def realestate_opportunities():

    opportunities = [

        {
            "ville": "Lisbonne",
            "rendement": "6.5%",
            "raison": "Forte demande locative"
        },

        {
            "ville": "Dubaï",
            "rendement": "7.2%",
            "raison": "Croissance démographique forte"
        },

        {
            "ville": "Athènes",
            "rendement": "6%",
            "raison": "Marché en rattrapage"
        }

    ]

    return {"real_estate": opportunities}

# ======================
# IDEES BUSINESS
# ======================

@app.get("/business/ideas")
def business_ideas():

    ideas = [

        {
            "idea": "Agence IA pour PME",
            "potential": "Très forte croissance"
        },

        {
            "idea": "Location courte durée automatisée",
            "potential": "Rentabilité élevée"
        },

        {
            "idea": "Newsletter premium marchés financiers",
            "potential": "Monétisation rapide"
        }

    ]

    return {"business_ideas": ideas}

# ======================
# TENDANCES ECONOMIQUES
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
