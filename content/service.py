from portfolio.service import get_user_portfolio 
from market.service import get_market
from advisor.service import (
    get_advisor_free,
    get_advisor_premium,
    get_advisor_elite
)

from sqlalchemy import text
from database import engine

from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# GENERIC AI CALL
# =========================
def call_ai(prompt):

    response = client.chat.completions.create(
    model="gpt-4o-mini",
    response_format={"type": "json_object"},
    messages=[{"role": "user", "content": prompt}]
    )
  
    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except Exception:
        return {"raw": content}


# =========================
# BUSINESS CONTENT
# =========================
def generate_business_content(budget, risk, goal):

    prompt = f"""
    Tu es un expert en business et entrepreneuriat.

    Budget: {budget}
    Niveau de risque: {risk}
    Objectif: {goal}

    Génère une réponse JSON :

    {{
      "analysis": "",
      "business_ideas": [
        {{
          "idea": "",
          "budget": "",
          "roi": ""
        }}
      ],
      "actions": [
        "action 1",
        "action 2"
      ]
    }}
    """

    return call_ai(prompt)


# =========================
# REAL ESTATE CONTENT
# =========================
def generate_real_estate_content(budget, risk, goal):

    prompt = f"""
    Tu es un expert en investissement immobilier.

    Budget: {budget}
    Niveau de risque: {risk}
    Objectif: {goal}

    Génère une réponse JSON :

    {{
      "analysis": "",
      "strategies": [
        {{
          "strategy": "",
          "budget": "",
          "roi": ""
        }}
      ],
      "actions": []
    }}
    """

    return call_ai(prompt)


# =========================
# USER PROFILE
# =========================
def get_user_profile(user_email):

    try:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT age, monthly_income, risk_profile
                FROM user_profiles
                WHERE user_email=:email
            """), {"email": user_email}).fetchone()

        if not row:
            return {}

        return {
            "age": row[0],
            "income": row[1],
            "risk": row[2]
        }

    except Exception:
        return {}


# =========================
# PERSONALIZED CONTENT (PREMIUM)
# =========================
def generate_personalized_content(user_email, goal):

    portfolio = get_user_portfolio(user_email)
    market = get_market("stock market")
    profile = get_user_profile(user_email)

    try:
        advisor = get_advisor("optimise mon portefeuille")
    except Exception:
        advisor = {"strategy": "diversification"}

    prompt = f"""
    Tu es un expert en finance globale.

    PROFIL: {profile}
    PORTFOLIO: {portfolio}
    CONSEIL: {advisor}
    MARCHÉ: {market}

    OBJECTIF: {goal}

    Réponds en JSON :

    {{
      "analysis": "",
      "actions": [],
      "portfolio_optimizations": [],
      "business_ideas": [],
      "real_estate": []
    }}
    """

    return call_ai(prompt)

