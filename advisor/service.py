from portfolio.service import get_user_portfolio
from market.service import get_market
from franchise.scanner import scan_franchise_opportunities
from sqlalchemy import text
from database import engine
from .engine import extract_budget, detect_risk, detect_goal, build_allocation
from openai import OpenAI
import os
import json


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# SIMPLE ADVISOR (COMPAT LAYER)
# =========================
def get_advisor(message: str):
    return advisor_logic(message)
    
def advisor_logic(message):

    budget = extract_budget(message)
    risk = detect_risk(message)
    goal = detect_goal(message)

    allocation = build_allocation(budget, risk)

    franchises = scan_franchise_opportunities(
        budget,
        risk,
        "france"
    )

    prompt = f"""
    Un utilisateur a {budget}€.
    Profil de risque: {risk}
    Objectif: {goal}

    Allocation:
    {allocation}

    Opportunités de franchises:
    {franchises} 

    Donne:
    - stratégie claire
    - actions concrètes
    - exemples d'investissements (actions, crypto, immo, business, crowdfunding)
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "budget": budget,
            "risk": risk,
            "goal": goal,
            "allocation": allocation,
            "franchises": franchises,
            "advice": response.choices[0].message.content
        }

    except Exception as e:
        return {"error": str(e)}


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
# PREMIUM ADVISOR
# =========================
def get_advisor_premium(user_email, message):

    try:
        portfolio = get_user_portfolio(user_email)
        market = get_market("stock market")
        profile = get_user_profile(user_email)
        franchises = scan_franchise_opportunities(
            profile.get("income", 1000),
            profile.get("risk", "medium"),
            "france"
        )

        prompt = f"""
        Tu es un conseiller financier élite.

        PROFIL:
        {profile}

        PORTFOLIO:
        {portfolio}

        MARCHÉ:
        {market}

        FRANCHISES:
        {franchises}

        DEMANDE:
        {message}

        Réponds STRICTEMENT en JSON :

        {{
          "allocation": {{
            "stocks": 0,
            "crypto": 0,
            "real_estate": 0,
            "cash": 0
          }},
          "rebalancing": [
            "actions à faire sur le portefeuille"
          ],
          "opportunities": [
            "opportunités immédiates à saisir"
          ],
          "business": [
            "idées business adaptées"
          ],
          "real_estate": [
            "stratégies immobilières"
          ],
          "marketing_content": "post prêt à publier"
          ],
          "franchise": [
          "opportunités adaptées"
          ]
           
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content

        try:
            result = json.loads(content)
        except:
            result = {"raw": content}

        return result

    except Exception as e:
        return {"error": str(e)}


# =========================
# AUTO ADVISOR ENGINE
# =========================
def get_advisor_auto(user_email):

    try:
        portfolio = get_user_portfolio(user_email)
        market = get_market("stock market")
        profile = get_user_profile(user_email)
        franchises = scan_franchise_opportunities(
            profile.get("income", 1000),
            profile.get("risk", "medium"),
            "france"
        )

        prompt = f"""
        Tu es un conseiller financier automatisé de niveau institutionnel.

        PROFIL UTILISATEUR:
        {profile}

        PORTFOLIO ACTUEL:
        {portfolio}

        CONTEXTE MARCHÉ:
        {market}

        OPPORTUNITÉS FRANCHISE:
        {franchises}

        Analyse en profondeur et détecte :

        - risques
        - opportunités
        - sur/sous-exposition
        - incohérences
        - actions immédiates

        Réponds STRICTEMENT en JSON :

        {{
          "alerts": [
            {{
              "type": "risk | opportunity",
              "asset": "",
              "message": ""
            }}
          ],
          "actions": [
            "action concrète 1",
            "action concrète 2"
          ],
          "rebalancing": {{
            "stocks": 0,
            "crypto": 0,
            "real_estate": 0,
            "cash": 0
          }},
          "portfolio_health": {{
            "score": 0,
            "comment": ""
          }},
          "franchise_opportunities": [
            {
              "name": "",
              "budget": "",
              "roi": "",
              "risk": ""
            }
          ],
          "opportunities": [
            "opportunité 1",
            "opportunité 2"
          ]
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content

        try:
            result = json.loads(content)
        except Exception:
            result = {
                "raw": content,
                "error": "invalid_json"
            }

        return result

    except Exception as e:
        return {"error": str(e)}

