from portfolio.service import get_user_portfolio
from advisor.service import get_advisor
from market.service import get_market
from openai import OpenAI
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# BUSINESS CONTENT
# =========================
def generate_business_content(budget, risk, goal):

    prompt = f"""
    Un utilisateur a {budget}€.
    Profil de risque: {risk}
    Objectif: {goal}

    Génère:
    - 3 idées de business adaptées
    - budget nécessaire pour chaque
    - étapes pour démarrer
    - potentiel de revenus
    - niveau de difficulté
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return str(e)


# =========================
# REAL ESTATE CONTENT
# =========================
def generate_real_estate_content(budget, risk, goal):

    prompt = f"""
    Un utilisateur a {budget}€.
    Profil de risque: {risk}
    Objectif: {goal}

    Génère:
    - 3 stratégies immobilières adaptées
    - type de bien
    - budget minimum
    - rendement estimé (%)
    - risques associés
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return str(e)


# =========================
# PERSONALIZED CONTENT
# =========================
def generate_personalized_content(user_email, goal):

    try:
        # =========================
        # 🔥 DATA SOURCES
        # =========================
        portfolio = get_user_portfolio(user_email)
        advisor = get_advisor("j’ai un capital, optimise moi ça")
        market = get_market("stock market")

        # =========================
        # 🧠 PROMPT IA
        # =========================
        prompt = f"""
        Tu es un expert en finance, business et investissement.

        Données utilisateur:
        PORTFOLIO:
        {portfolio}

        CONSEIL IA:
        {advisor}

        MARCHÉ:
        {market}

        OBJECTIF:
        {goal}

        Génère un contenu PERSONNALISÉ:

        - analyse du portefeuille
        - erreurs à corriger
        - opportunités immédiates
        - plan d’action concret (étapes)
        - idées business adaptées
        - stratégies immobilières adaptées

        Format:
        clair, structuré, actionnable
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return str(e)

