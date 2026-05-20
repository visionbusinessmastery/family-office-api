def compute_legacy_engine(payload: dict) -> dict:
    """
    Strategic, high-level legacy planning engine.
    It does not provide legal, tax, or financial advice; it structures questions
    and priorities for a qualified advisor conversation.
    """
    payload = payload or {}
    heirs_count = int(payload.get("heirs_count") or 0)
    vault_count = int(payload.get("vault_count") or 0)
    governance_rules = int(payload.get("governance_rules") or 0)
    international = bool(payload.get("international") or False)

    succession = min(100, heirs_count * 22 + vault_count * 8)
    governance = min(100, governance_rules * 28 + heirs_count * 8)
    protection = min(100, vault_count * 15 + governance_rules * 10)
    global_strategy = 70 if international else 35

    priorities = []
    if heirs_count == 0:
        priorities.append("Identifier les beneficiaires et leur niveau de preparation financiere.")
    if vault_count < 3:
        priorities.append("Centraliser les documents essentiels dans le Family Vault.")
    if governance_rules == 0:
        priorities.append("Rediger une premiere charte de gouvernance familiale.")
    if not international:
        priorities.append("Evaluer calmement l'exposition geographique et fiscale.")

    return {
        "scores": {
            "succession_planning": succession,
            "family_office_structure": governance,
            "asset_protection": protection,
            "expatriation_strategy": global_strategy,
            "trust_simulation": round((succession + protection) / 2),
            "wealth_transmission": round((succession + governance + protection) / 3),
        },
        "priorities": priorities[:5],
        "ethan_positioning": (
            "Conceptuel et strategique: Ethan prepare les bonnes questions, "
            "sans remplacer un conseil legal, fiscal ou patrimonial reglemente."
        ),
    }
