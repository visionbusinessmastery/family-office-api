import hashlib
import json
import re
import unicodedata


VISIBLE_STRUCTURE_PATTERNS = [
    r"^\s*(insight|action|next step|next best action|priorite|decision)\s*:",
    r"next best action",
    r"action simple\s*:",
    r"action prioritaire\s*:",
]

LEGACY_CONTENT_PATTERNS = [
    "ton score est",
    "ton score ",
    "score 39/100",
    "pour le cashflow",
    "clarifier la capacite mensuelle",
    "capacite mensuelle disponible",
]

BANNED_RENDERER_TAILS = [
    "Garde ce filtre simple.",
    "La suite doit rester legere.",
    "Ferme une option avant d'en ouvrir une autre.",
    "Moins d'options, plus de nettete.",
    "La discipline ici est de ne pas surconstruire.",
]

ETHAN_TEXT_ORIGIN = "ethan_output_renderer"


def _stable_index(seed, size):
    if size <= 0:
        return 0
    digest = hashlib.sha256(json.dumps(seed, sort_keys=True, default=str).encode()).hexdigest()
    return int(digest[:8], 16) % size


def _normalize(value) -> str:
    raw = str(value or "").lower()
    normalized = unicodedata.normalize("NFD", raw)
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return (
        normalized
        .replace("\u00c3\u00a9", "e")
        .replace("\u00c3\u00a8", "e")
        .replace("\u00c3\u00aa", "e")
        .replace("\u00c3\u00a0", "a")
        .replace("\u00c3\u00a2", "a")
    )


def _looks_legacy_or_structured(text) -> bool:
    normalized = _normalize(text)
    if any(_normalize(pattern) in normalized for pattern in LEGACY_CONTENT_PATTERNS):
        return True
    return False


def _strip_visible_labels(text):
    lines = []
    for line in str(text or "").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if any(re.search(pattern, cleaned, flags=re.IGNORECASE) for pattern in VISIBLE_STRUCTURE_PATTERNS):
            cleaned = re.sub(r"^\s*[^:]{1,40}:\s*", "", cleaned).strip()
            cleaned = re.sub(r"next best action\s*:?", "", cleaned, flags=re.IGNORECASE).strip()
        if cleaned:
            lines.append(cleaned)
    return " ".join(lines).strip()


def _context_phrase(context):
    life_context = context.get("life_context") if isinstance(context, dict) else {}
    life_context = life_context if isinstance(life_context, dict) else {}

    if life_context.get("time_constraint") and (
        life_context.get("has_children") or life_context.get("family_constraint")
    ):
        return "avec ton rythme et tes contraintes familiales"
    if life_context.get("time_constraint"):
        return "avec le temps disponible que tu as"
    if life_context.get("expertise"):
        return "en partant de ce que tu sais deja faire"
    if life_context.get("priority_goal"):
        return "en gardant ton objectif principal en face"
    return "avec le contexte disponible"


def _message_has(message, words):
    normalized = _normalize(message)
    return any(_normalize(word) in normalized for word in words)


def _profile(context, message):
    life_context = context.get("life_context") if isinstance(context, dict) else {}
    life_context = life_context if isinstance(life_context, dict) else {}
    businesses = life_context.get("businesses") or []

    return {
        "time_limited": bool(life_context.get("time_constraint")) or _message_has(
            message, ["peu de temps", "pas le temps", "temps limite", "charge mentale"]
        ),
        "has_children": bool(life_context.get("has_children") or life_context.get("family_constraint"))
        or _message_has(message, ["enfant", "enfants", "famille"]),
        "marketing": bool(life_context.get("expertise")) or _message_has(
            message, ["marketing", "communication", "commerce", "acquisition", "contenu"]
        ),
        "employee": _message_has(message, ["salarie", "cdi", "emploi", "2000"]),
        "business": bool(life_context.get("business_context") or businesses) or _message_has(
            message, ["entreprise", "business", "activite", "freelance", "individuelle"]
        ),
    }


def _clean_human_text(text):
    cleaned = _strip_visible_labels(text)
    for tail in BANNED_RENDERER_TAILS:
        cleaned = cleaned.replace(tail, "").strip()

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > 950:
        cleaned = cleaned[:947].rstrip() + "..."
    return cleaned


def _raw_signal(response_data):
    if not isinstance(response_data, dict):
        return ""
    raw = response_data.get("raw_llm_output") or response_data.get("raw_signal") or ""
    if _looks_legacy_or_structured(raw):
        return ""
    return _clean_human_text(raw)


def _sentence_from_signal(signal):
    if not signal:
        return ""
    sentence = re.split(r"(?<=[.!?])\s+", signal.strip())[0].strip()
    if len(sentence) > 260:
        sentence = sentence[:257].rstrip() + "..."
    return sentence


def _fallback_from_context(message, context, response_strategy):
    profile = _profile(context or {}, message)
    intent = (response_strategy or {}).get("primary_intent") or ""
    normalized_message = _normalize(message)

    if profile["marketing"] and profile["time_limited"] and profile["has_children"]:
        if "utiliser" in normalized_message or "entreprise" in normalized_message:
            return (
                "Ton entreprise marketing peut devenir un levier si tu la rends plus productisee. "
                "Je ne chercherais pas a vendre plus de prestations sur mesure: je construirais une offre standardisee, livrable vite, "
                "comme un diagnostic acquisition + plan d'action IA pour dirigeants de petites entreprises. "
                "La prochaine etape utile est de choisir une seule cible et d'ecrire une promesse assez precise pour etre envoyee en message direct."
            )
        if "revenu" in normalized_message or intent == "increase_income":
            return (
                "Vu ton temps limite et ton activite marketing, le meilleur levier n'est pas d'ajouter plus de travail: "
                "c'est de packager une offre courte, vendable et recurrente. Je partirais sur un audit marketing/IA simple, "
                "avec une promesse claire, un prix fixe et une option d'accompagnement mensuel leger. Cette semaine, ne cherche pas dix idees: "
                "ecris l'offre en une page et propose-la a trois contacts deja accessibles."
            )
        if "semaine" in normalized_message or "meilleure action" in normalized_message:
            return (
                "Cette semaine, je ferais une action commerciale minuscule mais concrete: reprendre ton expertise marketing et la transformer en une offre test. "
                "Pas de tunnel, pas de site, pas de nouveau projet. Juste une phrase de promesse, un prix indicatif et trois personnes a qui l'envoyer. "
                "Le but est de valider si ton savoir-faire peut generer du revenu sans consommer tes soirees."
            )
        if "investir" in normalized_message or "developper" in normalized_message:
            return (
                "Je privilegierais ton activite avant un nouvel investissement. Avec peu de temps et deux jeunes enfants, "
                "le capital le plus sous-exploite est ton expertise marketing, pas une allocation plus complexe. "
                "La bonne decision maintenant: creer une petite source de revenu recurrente a faible charge mentale, puis investir seulement l'excedent stable."
            )
        if "opportunite" in normalized_message or "profil" in normalized_message:
            return (
                "L'opportunite la plus coherente avec ton profil est une offre B2B courte autour de ton savoir-faire marketing, pas un projet digital lourd. "
                "Tu as besoin d'un format qui se vend cher, se livre vite et peut devenir recurrent. "
                "Je viserais une offre d'audit ou de pilotage mensuel leger pour PME locales qui veulent clarifier leur acquisition."
            )
        if "enfants" in normalized_message or "temps" in normalized_message:
            return (
                "Avec deux enfants en bas age, la strategie doit proteger ton energie. "
                "Je chercherais une action qui cree du revenu sans ouvrir un chantier permanent: une offre courte, un rendez-vous qualifie, une proposition simple. "
                "Ton indicateur n'est pas le nombre d'idees, c'est le nombre d'actions que tu peux vraiment terminer dans une semaine normale."
            )
        if "risque" in normalized_message:
            return (
                "Ton risque principal semble etre la dispersion: vouloir augmenter les revenus, investir et structurer le patrimoine en meme temps. "
                "Avec une charge familiale forte, la priorite est de choisir un seul levier de revenu simple et mesurable. "
                "Le bon test cette semaine: une offre, une cible, une action commerciale."
            )
        return (
            "Ta priorite n'est pas de tout optimiser: c'est de trouver un levier de revenu compatible avec ta vraie vie. "
            "Avec ton profil marketing et peu de temps disponible, je commencerais par transformer ton expertise en offre premium courte, "
            "plutot qu'en nouveau projet lourd. Une action utile: definir une offre precise que tu peux vendre sans y passer tes soirees."
        )

    if intent == "increase_income" or "revenu" in normalized_message:
        return (
            "Le levier le plus propre est de partir de ce que tu sais deja vendre ou produire, puis de le rendre plus recurrent. "
            "Cherche une offre simple, avec un resultat clair et un temps de livraison limite. L'objectif n'est pas plus d'activite, "
            "mais plus de valeur par heure."
        )

    if "risque" in normalized_message:
        return (
            "Le risque a surveiller est la dispersion: trop de pistes ouvertes reduisent la qualite des decisions. "
            "Garde une seule priorite visible cette semaine et mesure si elle ameliore vraiment ta marge de manoeuvre."
        )

    return (
        "La prochaine decision doit reduire la complexite tout en creant un resultat visible. "
        "Choisis l'action qui peut etre terminee cette semaine et qui rapproche le plus ton revenu, ton temps et ton patrimoine."
    )


def render_ethan_output(response_data, context=None, message=None, response_strategy=None, tier=None):
    """
    Single authorized human-text renderer for Ethan.

    Response Engine returns data only. Prompt Engine provides context only.
    This renderer is the only layer allowed to create the final user-facing
    Ethan sentence stored in `analysis`.
    """
    context = context or {}
    strategy = response_strategy or {}
    lens = strategy.get("cognitive_lens") or "human_context"
    counter = strategy.get("diversity_counter") or 0
    status = response_data.get("status") if isinstance(response_data, dict) else "empty"
    phrase = _context_phrase(context)
    signal = _raw_signal(response_data)
    premium = tier not in ["ESSENTIALS", "FREE", "BASIC", None]
    entry_mode = {
        "human_context": "observation_first",
        "insight": "insight_first",
        "question": "question_first",
        "risk": "risk_first",
        "action": "action_first",
        "financial": "observation_first",
    }.get(lens, "observation_first")
    density = "dense" if premium and status != "empty" else "medium"
    transition = "direct"

    if signal and status != "empty":
        return signal

    variants = {
        "insight_first": [_fallback_from_context(message, context, strategy)],
        "action_first": [_fallback_from_context(message, context, strategy)],
        "risk_first": [_fallback_from_context(message, context, strategy)],
        "question_first": [_fallback_from_context(message, context, strategy)],
        "observation_first": [_fallback_from_context(message, context, strategy)],
    }
    selected_variants = variants.get(entry_mode) or variants["observation_first"]
    index = _stable_index(
        {
            "message": message,
            "lens": lens,
            "counter": counter,
            "tier": tier,
            "status": status,
            "entry": entry_mode,
            "density": density,
            "transition": transition,
        },
        len(selected_variants),
    )
    rendered = selected_variants[index]
    return _clean_human_text(rendered)
