from openai import OpenAI
import os
from .scanner import scan_franchise_opportunities

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_franchise_advisor(data):

    opportunities = scan_franchise_opportunities(
        data.budget,
        data.risk,
        data.country,
        data.sector
    )

    prompt = f"""
    Tu es un expert en franchise business.

    Budget: {data.budget}€
    Pays: {data.country}
    Risque: {data.risk}
    Secteur: {data.sector}

    Opportunités détectées:
    {opportunities}

    Donne:
    - meilleure franchise à choisir
    - stratégie d’entrée
    - risques
    - rentabilité estimée
    - plan d’action étape par étape
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "opportunities": opportunities,
        "advice": response.choices[0].message.content
    }
