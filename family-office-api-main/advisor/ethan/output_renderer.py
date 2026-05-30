import re
import unicodedata


VISIBLE_STRUCTURE_PATTERNS = [
    r"^\s*(insight|action|next step|next best action|priorite|decision)\s*:",
    r"next best action\s*:?",
    r"action simple\s*:",
    r"action prioritaire\s*:",
]

LEGACY_CONTENT_PATTERNS = [
    "ton score est",
    "score 39/100",
    "pour le cashflow, ton score",
    "clarifier la capacite mensuelle",
    "capacite mensuelle disponible",
    "garde ce filtre simple",
]

ETHAN_TEXT_ORIGIN = "ethan_output_renderer"

LIGHT_SOCIAL_PATTERNS = [
    "bonjour",
    "salut",
    "hello",
    "coucou",
    "comment vas tu",
    "comment ca va",
    "merci",
]


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


def _looks_legacy(text) -> bool:
    normalized = _normalize(text)
    return any(_normalize(pattern) in normalized for pattern in LEGACY_CONTENT_PATTERNS)


def _clean_visible_labels(text):
    lines = []
    for line in str(text or "").splitlines():
        cleaned = line.strip()
        if not cleaned:
            lines.append("")
            continue
        if any(
            re.search(pattern, cleaned, flags=re.IGNORECASE)
            for pattern in VISIBLE_STRUCTURE_PATTERNS
        ):
            cleaned = re.sub(r"^\s*[^:]{1,40}:\s*", "", cleaned).strip()
            cleaned = re.sub(
                r"next best action\s*:?",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).strip()
        lines.append(cleaned)

    compact = "\n".join(lines).strip()
    compact = re.sub(r"\n{3,}", "\n\n", compact)
    compact = re.sub(r"[ \t]+", " ", compact)
    return compact


def _raw_signal(response_data):
    if not isinstance(response_data, dict):
        return ""
    raw = response_data.get("raw_llm_output") or response_data.get("raw_signal") or ""
    if _looks_legacy(raw):
        return ""
    return _clean_visible_labels(raw)


def _is_light_social_message(message) -> bool:
    normalized = _normalize(message)
    return any(pattern in normalized for pattern in LIGHT_SOCIAL_PATTERNS)


def _unavailable_text(message=None, status=None):
    if _is_light_social_message(message):
        return (
            "Bonjour, je vais bien, merci. Je suis la avec ton contexte White Rock. "
            "Dis-moi ce que tu veux regarder maintenant: une decision, un risque, une opportunite "
            "ou simplement ta prochaine action utile."
        )

    if status == "openai_unconfigured":
        return (
            "Je suis bien connecte a ton contexte White Rock, mais le moteur IA n'est pas disponible "
            "cote serveur pour l'instant. Je prefere etre transparent plutot que d'inventer une reponse: "
            "verifie la configuration OpenAI sur Render, puis relance Ethan."
        )

    return (
        "Je suis la, mais je n'ai pas recu une reponse complete du moteur IA sur cette demande. "
        "Pour eviter d'inventer, je prefere relancer proprement: repose ta question dans une phrase simple "
        "et Ethan repartira du contexte backend actuel."
    )


def render_ethan_output(response_data, context=None, message=None, response_strategy=None, tier=None):
    """
    Single authorized human-text gate for Ethan.

    Ethan is LLM-first: OpenAI produces the advisor answer from backend context.
    This layer must stay cosmetic and contractual: it strips legacy labels,
    blocks old score/cashflow templates, and returns a neutral unavailable
    message only when the LLM produced no usable text.
    """
    status = response_data.get("status") if isinstance(response_data, dict) else "empty"
    llm_status = response_data.get("llm_status") if isinstance(response_data, dict) else None
    signal = _raw_signal(response_data)

    if signal and status != "empty":
        return signal

    return _unavailable_text(message=message, status=llm_status)
