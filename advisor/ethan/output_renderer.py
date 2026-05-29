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
    return any(
        re.search(pattern, normalized, flags=re.IGNORECASE | re.MULTILINE)
        for pattern in VISIBLE_STRUCTURE_PATTERNS
    )


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


def _raw_signal(response_data):
    if not isinstance(response_data, dict):
        return ""
    raw = response_data.get("raw_llm_output") or response_data.get("raw_signal") or ""
    if _looks_legacy_or_structured(raw):
        return ""
    return _strip_visible_labels(raw)


def _sentence_from_signal(signal):
    if not signal:
        return ""
    sentence = re.split(r"(?<=[.!?])\s+", signal.strip())[0].strip()
    if len(sentence) > 260:
        sentence = sentence[:257].rstrip() + "..."
    return sentence


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
    signal = _sentence_from_signal(_raw_signal(response_data))
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
        variants = {
            "insight_first": [
                f"{signal} Ce qui compte ici, {phrase}, c'est de ne garder qu'une avancee vraiment executable.",
                f"{phrase.capitalize()}, je retiendrais surtout ceci: {signal} Le reste peut attendre.",
            ],
            "action_first": [
                f"Garde une seule avancee concrete cette semaine. {signal}",
                f"Commence par le geste le plus simple a terminer, puis utilise ce signal: {signal}",
            ],
            "risk_first": [
                f"Le risque serait de transformer ca en plan trop lourd. {signal}",
                f"Attention a la surcharge de decision: {signal}",
            ],
            "question_first": [
                f"La bonne question est: qu'est-ce qui devient plus simple apres cette decision ? {signal}",
                f"Avant d'ajouter une option, demande-toi ce que ce signal allege vraiment: {signal}",
            ],
            "observation_first": [
                f"{phrase.capitalize()}, ce signal merite surtout d'etre simplifie: {signal}",
                f"Ce que j'observe ici est assez net: {signal}",
            ],
        }
        if premium and density == "dense":
            variants.setdefault(entry_mode, []).append(
                f"{signal} Je le lirais comme un arbitrage de charge mentale: avance sur ce qui cree de la clarte sans consommer plus d'energie."
            )
    else:
        variants = {
            "insight_first": [
                f"Le point utile ici, {phrase}, c'est de ne pas transformer la question en plan trop lourd.",
                f"Je prefere rester sobre: {phrase}, la bonne suite n'est pas d'ajouter plus d'analyse.",
            ],
            "action_first": [
                f"Choisis une avancee tres simple et executable cette semaine, {phrase}.",
                f"Avance sur une action que tu peux terminer vite, puis reviens au reste apres.",
            ],
            "risk_first": [
                f"Le piege serait d'ouvrir trop de fronts en meme temps. {phrase.capitalize()}, reduis d'abord la charge de decision.",
                f"Ce qui merite attention, c'est la complexite ajoutee. Garde la prochaine etape courte et verifiable.",
            ],
            "question_first": [
                f"Quelle decision rend la suite plus legere ? {phrase.capitalize()}, c'est le bon filtre maintenant.",
                f"Demande-toi ce qui peut etre termine avant la fin de semaine, sans ouvrir un nouveau chantier.",
            ],
            "observation_first": [
                f"{phrase.capitalize()}, le mouvement le plus propre est une avancee courte, visible et facile a verifier.",
                f"Ce que j'observe ici: il vaut mieux reduire la charge de decision que chercher une analyse parfaite.",
            ],
        }
        if premium and density == "dense":
            variants.setdefault(entry_mode, []).append(
                f"Il y a probablement un arbitrage a garder simple: {phrase}, la meilleure decision est celle qui cree de la clarte sans consommer plus d'energie."
            )

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

    transition_tail = {
        "direct": "Garde ce filtre simple.",
        "soft_pivot": "La suite doit rester legere.",
        "contrast": "Ferme une option avant d'en ouvrir une autre.",
        "compression": "Moins d'options, plus de nettete.",
        "quiet_challenge": "La discipline ici est de ne pas surconstruire.",
    }.get(transition)

    if transition_tail and density == "medium":
        return f"{rendered} {transition_tail}"

    return rendered
