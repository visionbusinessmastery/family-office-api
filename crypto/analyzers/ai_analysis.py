import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_crypto_ai(data):

    prompt = f"""
    Analyse cette crypto :

    {data}

    Donne :
    - tendance (bullish/bearish)
    - stratégie recommandée
    - niveau de risque
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
