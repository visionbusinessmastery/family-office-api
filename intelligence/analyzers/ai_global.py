import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def global_ai_analysis(data):

    prompt = f"""
    Analyse ce portefeuille :

    {data}

    Donne :
    - stratégie globale
    - allocation recommandée
    - risques
    - opportunités
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return str(e)

def global_score(return_rate, risk, duration):
    score = 0

    score += return_rate * 2

    if risk == "low":
        score += 20
    elif risk == "medium":
        score += 10

    if duration < 24:
        score += 10

    return min(score, 100)

def adapt_strategy(profile, investment):
    
    if profile["age"] > 50:
        investment["risk"] = "low"
    
    if profile["revenus_mensuels"] < 2000:
        investment["max_budget"] = 100
    
    return investment
