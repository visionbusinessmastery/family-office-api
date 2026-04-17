import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def global_ai_analysis(data):

    prompt = f"""
    Analyse ce portefeuille :

    Budget: {data.get("budget")}
    Risk: {data.get("risk")}
    Allocation: {data.get("allocation")}

    Donne :
    - stratégie globale
    - allocation recommandée
    - risques
    - opportunités

    Réponds de manière structurée et professionnelle.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return str(e)
