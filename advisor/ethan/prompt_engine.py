import json

from advisor.ethan.context_engine import compact_context, compact_portfolio


def build_advisor_messages(
    context,
    portfolio,
    opportunities,
    memory,
    message,
    plan,
    tier,
    complexity,
    response_strategy,
):
    system_prompt = (
        "Tu recois uniquement le contexte backend White Rock. "
        "Utilise seulement les donnees fournies: profil, entitlements, memoire, portefeuille, missions, opportunites et strategie interne. "
        "Ne fabrique aucune donnee, aucun chiffre, aucun actif et aucune opportunite. "
        "Produis une matiere cognitive interne utile au moteur de rendu Ethan. "
        "N'ajoute pas de format obligatoire, pas de rubriques imposees, pas de bloc final, pas de texte de secours linguistique."
    )

    compressed_context = {
        "ethan_tier": tier,
        "plan": plan,
        "complexity": complexity,
        "profile": compact_context(context),
        "portfolio": compact_portfolio(portfolio),
        "opportunities": opportunities[:3] if isinstance(opportunities, list) else opportunities,
        "memory": memory,
        "response_strategy": response_strategy,
    }

    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Contexte compresse WHITE ROCK:\n"
                f"{json.dumps(compressed_context, separators=(',', ':'), ensure_ascii=False)}\n\n"
                f"Question utilisateur: {message}"
            ),
        },
    ]
