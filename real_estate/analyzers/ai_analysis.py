import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_property_ai(prop):

    prompt = f"""
    Analyse cet investissement immobilier :

    Ville : {prop.get("city", "N/A")}
    Prix : {prop["price"]}
    Surface : {prop["surface"]} m²
    Prix au m² : {round(prop["price"] / prop["surface"], 2)}

    Donne une réponse structurée :

    - potentiel : faible / moyen / élevé
    - stratégie : location / flip / revente / éviter
    - points forts
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
