import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_business_ai(data, mode):

    prompt = f"""
    Analyse cette opportunité business :

    Mode : {mode}
    Données : {data}

    Donne :
    - potentiel
    - rentabilité estimée
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
