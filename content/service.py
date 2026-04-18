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
