from openai import OpenAI
import os
from .engine import extract_budget, detect_risk, detect_goal, build_allocation

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def advisor_logic(message):

    budget = extract_budget(message)
    risk = detect_risk(message)
    goal = detect_goal(message)

    allocation = build_allocation(budget, risk)

    prompt = f"""
    Un utilisateur a {budget}€.
    Profil de risque: {risk}
    Objectif: {goal}

    Allocation:
    {allocation}

    Donne:
    - stratégie claire
    - actions concrètes
    - exemples d'investissements (actions, crypto, immo, business, crowdfunding)
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "budget": budget,
            "risk": risk,
            "goal": goal,
            "allocation": allocation,
            "advice": response.choices[0].message.content
        }

    except Exception as e:
        return {"error": str(e)}
