import requests
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_property_ai(property):

    prompt = f"""
    Analyse cette opportunité immobilière :

    Titre : {property['title']}
    Prix : {property['price']}
    Surface : {property['surface']}

    Donne :
    - potentiel (faible / moyen / élevé)
    - stratégie recommandée
    - risques
    - note sur 10
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI error: {str(e)}"
