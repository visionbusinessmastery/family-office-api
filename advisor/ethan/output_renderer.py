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


def _unavailable_text():
    return (
        "Je n'ai pas pu acceder correctement au moteur Ethan sur cette demande. "
        "Je prefere ne pas inventer une recommandation patrimoniale a partir d'un signal incomplet. "
        "Relance ta question dans un instant: la reponse repartira du contexte backend actuel."
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
    signal = _raw_signal(response_data)

    if signal and status != "empty":
        return signal

    return _unavailable_text()
