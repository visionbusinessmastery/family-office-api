from portfolio.service import get_user_portfolio
from market.service import get_market
from advisor.service import get_advisor
from sqlalchemy import text
from database import engine

from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# GET USER PROFILE
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

    except:
        return {}


# =========================
# PERSONALIZED CONTENT (UPGRADED)
# =========================
def generate_personalized_content(user_email, goal):

    try:
        # =========================
        # 🔥 DATA SOURCES
        # =========================
        portfolio = get_user_portfolio(user_email)
        market = get_market("stock market")
        profile = get_user_profile(user_email)

        # =========================
        # 🛑 SAFE ADVISOR
        # =========================
        try:
            advisor = get_advisor("optimise mon portefeuille")
        except:
            advisor = {"strategy": "diversification"}

        # =========================
        # 🧠 PROMPT STRUCTURÉ
        # =========================
        prompt = f"""
        Tu es un expert en finance, business et investissement.

        PROFIL UTILISATEUR:
        {profile}

        PORTFOLIO:
        {portfolio}

        CONSEIL IA:
        {advisor}

        CONTEXTE MARCHÉ:
        {market}

        OBJECTIF:
        {goal}

        Analyse et génère une réponse STRUCTURÉE.

        Réponds STRICTEMENT en JSON avec :

        {{
          "analysis": "analyse claire du portefeuille et du profil",
          "actions": [
            "actions concrètes à court terme",
            "optimisations à faire"
          ],
          "business_ideas": [
            {{
              "idea": "",
              "budget": "",
              "potential": ""
            }}
          ],
          "real_estate_strategies": [
            {{
              "strategy": "",
              "budget": "",
              "roi": ""
            }}
          ],
          "viral_post": "post Facebook engageant basé sur cette analyse"
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return {
            "error": str(e)
        }


# =========================
# COMPAT LAYER (FIX IMPORT ERROR)
# =========================

def generate_business_content(user_email, goal="business"):
    return generate_personalized_content(user_email, goal)


def generate_real_estate_content(user_email, goal="real_estate"):
    return generate_personalized_content(user_email, goal)
    except Exception as e:
        return str(e)

