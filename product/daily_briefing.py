from datetime import datetime


def _num(value, default=0.0):
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return float(default)


def _round(value, digits=2):
    return round(_num(value), digits)


def _trajectory_impact(mission: dict | None, data_profile: dict, risk: str, opportunity: str) -> dict:
    mission_key = str((mission or {}).get("key") or "").lower()
    monthly_capacity = _num(data_profile.get("monthly_capacity"))
    mobilizable_liquidity = _num(data_profile.get("mobilizable_liquidity"))
    completion = _num(data_profile.get("completion_percent"))

    if "security" in mission_key or "emergency" in mission_key or "reserve" in mission_key:
        dimension = "Securite"
        effect = "Renforce la resilience avant d'accelerer la trajectoire."
        metric = "Reserve et liquidite mobilisable"
    elif "income" in mission_key or "cashflow" in mission_key or monthly_capacity > 0:
        dimension = "Cashflow"
        effect = "Transforme la marge mensuelle en vitesse de progression."
        metric = "Capacite mensuelle"
    elif "portfolio" in mission_key or "allocation" in mission_key or "divers" in mission_key:
        dimension = "Allocation"
        effect = "Ameliore la lisibilite du risque et la qualite de l'exposition."
        metric = "Structure d'actifs"
    elif "transmission" in mission_key or "family" in mission_key or "governance" in mission_key:
        dimension = "Gouvernance"
        effect = "Rend la trajectoire plus transmissible et mieux documentee."
        metric = "Protection et transmission"
    elif completion < 70:
        dimension = "Donnees"
        effect = "Augmente la fiabilite des projections avant decision lourde."
        metric = "Completion du cockpit"
    elif mobilizable_liquidity > 0:
        dimension = "Liquidite mobilisable"
        effect = "Convertit une partie du cash disponible en option de progression prudente."
        metric = "Liquidite deployable"
    else:
        dimension = "Pilotage"
        effect = "Transforme le briefing en action suivie et mesurable."
        metric = "Execution"

    return {
        "dimension": dimension,
        "effect": effect,
        "metric": metric,
        "risk_link": risk,
        "opportunity_link": opportunity,
        "reading": f"Cette action agit d'abord sur {dimension.lower()}: {effect.lower()}",
    }


def _priority_context(
    data_profile: dict,
    score: int,
    mission: dict | None,
    risk: str,
    trajectory_impact: dict,
) -> dict:
    monthly_income = _num(data_profile.get("monthly_income"))
    monthly_expenses = _num(data_profile.get("monthly_expenses"))
    cashflow = monthly_income - monthly_expenses
    liquid_assets = _num(data_profile.get("liquid_assets"))
    debt_total = _num(data_profile.get("debt_total"))
    completion = _num(data_profile.get("completion_percent"))
    mission_progress = _num((mission or {}).get("progress_percent"))
    mission_key = str((mission or {}).get("key") or "").lower()

    priority_score = 35
    reasons = []

    if completion < 60:
        priority_score += 18
        reasons.append("les donnees restent incompletes")
    if monthly_expenses > 0 and liquid_assets < monthly_expenses * 6:
        priority_score += 20
        reasons.append("la reserve de securite reste sous 6 mois")
    if cashflow <= 0 and (monthly_income > 0 or monthly_expenses > 0):
        priority_score += 18
        reasons.append("le cashflow ne degage pas encore de marge")
    if debt_total > monthly_income * 12 and monthly_income > 0:
        priority_score += 12
        reasons.append("le poids de dette merite une vigilance")
    if mission and mission_progress < 100:
        priority_score += 12
        reasons.append("une mission prioritaire reste ouverte")
    if score >= 70 and mission_key.startswith("unlock"):
        priority_score += 8
        reasons.append("le niveau atteint rend le prochain palier pertinent")

    priority_score = max(1, min(100, int(priority_score)))

    if not reasons:
        reasons.append("elle transforme le briefing en progression mesurable")

    why_today = "Cette action est prioritaire aujourd'hui car " + ", ".join(reasons[:2]) + "."
    expected_outcome = (
        f"Resultat attendu: ameliorer {str(trajectory_impact.get('dimension') or 'le pilotage').lower()} "
        f"et rendre la prochaine decision plus fiable."
    )

    if mission_key == "complete_finance":
        alternative_action = "Alternative rapide: renseigner seulement une ligne de revenu et une ligne de charge."
    elif mission_key == "add_first_asset":
        alternative_action = "Alternative rapide: ajouter un seul actif principal, meme avec une valeur approximative."
    elif "unlock" in mission_key:
        alternative_action = "Alternative rapide: relire les benefices du palier sans changer d'abonnement aujourd'hui."
    elif cashflow > 0:
        alternative_action = "Alternative rapide: definir un montant mensuel test, sans automatisation immediate."
    else:
        alternative_action = "Alternative rapide: noter la decision et la reevaluer dans le prochain briefing."

    return {
        "priority_score": priority_score,
        "why_today": why_today,
        "expected_outcome": expected_outcome,
        "alternative_action": alternative_action,
    }


def _find_unread_academy_lesson(wealth_academy: dict, mission: dict | None):
    linked_lesson = (mission or {}).get("linked_academy_lesson") or {}
    if linked_lesson and not linked_lesson.get("completed"):
        return linked_lesson

    recommended = wealth_academy.get("recommended") or {}
    if recommended and not recommended.get("completed"):
        return {
            "module_key": recommended.get("module_key"),
            "module_title": recommended.get("module_title"),
            "lesson_key": recommended.get("lesson_key"),
            "lesson_title": recommended.get("lesson_title"),
            "duration": recommended.get("duration"),
            "reason": recommended.get("why_now"),
            "completed": recommended.get("completed"),
        }

    for module in wealth_academy.get("modules") or []:
        for lesson in module.get("lessons") or []:
            if not lesson.get("completed"):
                return {
                    "module_key": module.get("key"),
                    "module_title": module.get("title"),
                    "lesson_key": lesson.get("key"),
                    "lesson_title": lesson.get("title"),
                    "duration": lesson.get("duration"),
                    "reason": lesson.get("outcome"),
                    "completed": False,
                }

    return None


def _build_primary_action(
    missions: list[dict],
    wealth_academy: dict | None,
    daily_loop: dict | None,
    fallback_title: str,
    fallback_description: str,
) -> dict:
    missions = missions or []
    wealth_academy = wealth_academy or {}
    daily_loop = daily_loop or {}
    tasks = daily_loop.get("tasks") or []
    today_actions = daily_loop.get("today_actions") or {}

    open_task = next(
        (task for task in tasks if task.get("status") not in {"done", "cancelled"}),
        None,
    )

    if today_actions and not open_task:
        last_action_key = next(iter(today_actions.keys()), None)
        return {
            "type": "review",
            "title": "Suivi du jour",
            "description": "Une decision est deja enregistree aujourd'hui. Le bon mouvement est maintenant de laisser la boucle se consolider ou de relire la progression.",
            "cta_label": "Suivi enregistre",
            "xp": 0,
            "why": f"White Rock evite de redemander une decision alors que l'action {last_action_key or 'du jour'} est deja captee.",
            "locked": True,
        }

    if open_task:
        return {
            "type": "task",
            "title": open_task.get("title") or "Terminer une action suivie",
            "description": open_task.get("description") or "Une tache issue du briefing reste ouverte.",
            "cta_label": "Marquer comme fait",
            "task_id": open_task.get("id"),
            "mission_key": open_task.get("mission_key"),
            "xp": 30,
            "why": "Terminer une tache ouverte evite d'empiler de nouvelles recommandations.",
        }

    ready_mission = next(
        (item for item in missions if item.get("status") == "ready" and not item.get("completed")),
        None,
    )
    if ready_mission:
        return {
            "type": "mission",
            "title": ready_mission.get("title") or "Valider une mission",
            "description": ready_mission.get("linked_daily_action") or ready_mission.get("description"),
            "cta_label": "Valider mission",
            "mission_key": ready_mission.get("key"),
            "xp": int(ready_mission.get("xp") or 0),
            "why": "Cette mission est prete car les donnees backend confirment que le jalon est atteint.",
        }

    open_mission = next((item for item in missions if not item.get("completed")), None)
    unread_lesson = _find_unread_academy_lesson(wealth_academy, open_mission)
    if unread_lesson:
        return {
            "type": "academy",
            "title": unread_lesson.get("lesson_title") or "Lire une lecon utile",
            "description": unread_lesson.get("reason") or "Cette lecon aide a debloquer la prochaine action.",
            "cta_label": "Marquer comme lu",
            "lesson_key": unread_lesson.get("lesson_key"),
            "module_key": unread_lesson.get("module_key"),
            "duration": unread_lesson.get("duration"),
            "xp": 15,
            "why": "La prochaine action gagne en clarte si cette lecon courte est validee.",
        }

    return {
        "type": "decision",
        "title": fallback_title or "Decision du jour",
        "description": fallback_description,
        "cta_label": "Decider",
        "xp": 20,
        "why": "Aucun jalon immediat n'est pret: le briefing propose une decision simple a enregistrer.",
    }


def build_ceo_daily_briefing(
    data_profile: dict,
    score: int,
    plan: str,
    missions: list[dict] | None = None,
    mission_control: dict | None = None,
    future_view: dict | None = None,
    opportunity_radar: dict | None = None,
    board_briefing: dict | None = None,
    first_name: str | None = None,
    wealth_academy: dict | None = None,
    daily_loop: dict | None = None,
) -> dict:
    data_profile = data_profile or {}
    missions = missions or []
    mission_control = mission_control or {}
    future_view = future_view or {}
    opportunity_radar = opportunity_radar or {}
    board_briefing = board_briefing or {}

    visible_wealth = _num(data_profile.get("current_wealth"))
    projected_wealth = _num(data_profile.get("projection_wealth") or visible_wealth)
    monthly_income = _num(data_profile.get("monthly_income"))
    monthly_expenses = _num(data_profile.get("monthly_expenses"))
    cashflow = monthly_income - monthly_expenses
    monthly_capacity = _num(data_profile.get("monthly_capacity") or max(cashflow, 0))
    liquid_assets = _num(data_profile.get("liquid_assets"))
    security_reserve = _num(data_profile.get("security_reserve"))
    mobilizable_liquidity = _num(data_profile.get("mobilizable_liquidity"))
    completion = _num(data_profile.get("completion_percent"))
    freedom_target = 1_500_000
    freedom_progress = min(100, (projected_wealth / freedom_target) * 100) if freedom_target else 0

    mission = next((item for item in missions if not item.get("completed")), None)
    if not mission and missions:
        mission = missions[0]

    risk = (mission_control.get("risk") or {}).get("description") or board_briefing.get("main_risk")
    if not risk:
        if monthly_expenses > 0 and liquid_assets < monthly_expenses * 6:
            risk = "Epargne de securite a renforcer avant d'accelerer."
        elif completion < 60:
            risk = "Donnees patrimoniales encore incompletes."
        else:
            risk = "Aucun risque prioritaire critique aujourd'hui."

    opportunity = (
        (opportunity_radar.get("items") or [{}])[0].get("title")
        or (mission_control.get("opportunity") or {}).get("description")
        or board_briefing.get("main_opportunity")
    )
    if not opportunity:
        if mobilizable_liquidity > 0:
            opportunity = "Une partie de la liquidite peut etre transformee en trajectoire prudente."
        elif monthly_capacity > 0:
            opportunity = "Ta capacite mensuelle peut alimenter une progression reguliere."
        else:
            opportunity = "Le prochain levier est la clarification des donnees."

    recommended_action = (
        (mission_control.get("decision") or {}).get("action")
        or board_briefing.get("next_step")
        or (mission or {}).get("description")
    )
    if not recommended_action:
        if monthly_capacity > 0:
            recommended_action = f"Allouer {round(monthly_capacity * 0.7)} EUR/mois a une action long terme apres reserve."
        else:
            recommended_action = "Ajouter une donnee utile pour rendre la prochaine decision mesurable."

    if cashflow > 0:
        headline = "Tu disposes d'une marge de manoeuvre a transformer en progression."
    elif visible_wealth > 0:
        headline = "Ton patrimoine est suivi; la priorite est de clarifier la prochaine action."
    else:
        headline = "La priorite est de construire ton point de depart patrimonial."

    trajectory_impact = _trajectory_impact(mission, data_profile, risk, opportunity)
    priority_context = _priority_context(data_profile, score, mission, risk, trajectory_impact)
    primary_action = _build_primary_action(
        missions,
        wealth_academy,
        daily_loop,
        (mission or {}).get("title") or "Action recommandee",
        recommended_action,
    )

    return {
        "version": "ceo-daily-briefing-v1",
        "generated_at": datetime.utcnow().isoformat(),
        "title": "CEO Daily Briefing",
        "greeting": f"Bonjour {first_name}," if first_name else "Bonjour,",
        "headline": headline,
        "plan": plan,
        "metrics": {
            "visible_wealth": _round(visible_wealth),
            "projected_wealth": _round(projected_wealth),
            "wealth_delta": _round(projected_wealth - visible_wealth),
            "financial_freedom_progress": round(freedom_progress, 1),
            "wealth_score": int(score or 0),
            "monthly_cashflow": _round(cashflow),
            "monthly_capacity": _round(monthly_capacity),
            "completion_percent": round(completion, 1),
        },
        "risk": {
            "title": "Risque principal",
            "description": risk,
        },
        "opportunity": {
            "title": "Opportunite",
            "description": opportunity,
        },
        "recommended_action": {
            "title": primary_action.get("title") or (mission or {}).get("title") or "Action recommandee",
            "description": primary_action.get("description") or recommended_action,
            "estimated_time": primary_action.get("duration") or "2 minutes",
            "source": "backend",
            "mission_key": primary_action.get("mission_key") or (mission or {}).get("key"),
            "mission_xp": primary_action.get("xp") or (mission or {}).get("xp") or 0,
            "action_type": primary_action.get("type"),
            "lesson_key": primary_action.get("lesson_key"),
            "task_id": primary_action.get("task_id"),
        },
        "primary_action": primary_action,
        "trajectory_impact": trajectory_impact,
        **priority_context,
        "actions": [
            {"key": "decide", "label": "Decider", "status": "available"},
            {"key": "ignore", "label": "Ignorer", "status": "available"},
            {"key": "automate", "label": "Automatiser", "status": "preview"},
        ],
        "weekly_bridge": {
            "monday": "Choisir la decision utile de la semaine.",
            "friday": "Mesurer ce qui a avance et preparer la prochaine decision.",
        },
        "future_bridge": {
            "label": "Projection suivie",
            "scenarios": future_view.get("scenarios") or [],
            "assumption": future_view.get("assumption"),
        },
    }
