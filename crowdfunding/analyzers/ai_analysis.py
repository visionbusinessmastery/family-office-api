import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_project_ai(project):

    prompt = f"""
    Analyse cet investissement crowdfunding :

    Projet : {project['name']}
    Rendement : {project['expected_return']}%
    Risque : {project['risk']}
    Durée : {project['duration']} mois

    Donne :
    - potentiel
    - stratégie
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
