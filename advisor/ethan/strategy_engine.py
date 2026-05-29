import hashlib
import json


OUTPUT_STYLES = [
    "quiet_analyst",
    "strategic_advisor",
    "human_coach",
    "risk_lens",
    "action_trigger",
]

STRATEGIC_ANGLES = [
    "observation",
    "insight",
    "suggestion",
    "risk_lens",
    "question",
    "action_intuition",
]

COGNITIVE_LENSES = [
    "human_context",
    "insight",
    "question",
    "risk",
    "action",
    "financial",
]


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def detect_primary_intent(message):
    normalized = (message or "").lower()

    if any(word in normalized for word in ["revenu", "gagner", "business", "offre", "vente", "client"]):
        return "increase_income"
    if any(word in normalized for word in ["risque", "securite", "proteger", "concentration", "perdre"]):
        return "reduce_risk"
    if any(word in normalized for word in ["cashflow", "budget", "charge", "liquidite", "tresorerie"]):
        return "optimize_cashflow"
    if any(word in normalized for word in ["investir", "allocation", "portfolio", "portefeuille", "etf", "action", "crypto"]):
        return "invest"
    if any(word in normalized for word in ["priorite", "quoi faire", "action", "prochaine", "maintenant"]):
        return "prioritize_actions"
    if any(word in normalized for word in ["comprendre", "clarifier", "situation", "diagnostic"]):
        return "clarify_situation"

    return "prioritize_actions"


def _rotate_choice(options, previous, seed):
    candidates = [item for item in options if item != previous] or list(options)
    if not candidates:
        return None

    index = int(stable_hash({"seed": seed})[:8], 16) % len(candidates)
    return candidates[index]


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _select_cognitive_lens(primary_intent, previous_lens, diversity_counter, message):
    if previous_lens == "action":
        candidates = ["insight", "question"]
    else:
        candidates = list(COGNITIVE_LENSES)
        if previous_lens == "financial":
            candidates = [lens for lens in candidates if lens != "financial"]
        if primary_intent != "optimize_cashflow":
            candidates = [lens for lens in candidates if lens != "financial"]

    candidates = [lens for lens in candidates if lens != previous_lens] or list(COGNITIVE_LENSES)
    seed = f"{message}:{primary_intent}:{diversity_counter}:lens"
    return candidates[int(stable_hash({"seed": seed})[:8], 16) % len(candidates)]


def _style_for_lens(lens, previous_style, diversity_counter, message):
    preferred = {
        "human_context": ["human_coach", "quiet_analyst"],
        "insight": ["quiet_analyst", "strategic_advisor"],
        "question": ["quiet_analyst", "human_coach"],
        "risk": ["risk_lens", "quiet_analyst"],
        "action": ["action_trigger", "strategic_advisor"],
        "financial": ["strategic_advisor", "quiet_analyst"],
    }.get(lens, OUTPUT_STYLES)

    candidates = [style for style in preferred if style != previous_style] or [
        style for style in OUTPUT_STYLES if style != previous_style
    ] or list(OUTPUT_STYLES)
    seed = f"{message}:{lens}:{diversity_counter}:style"
    return candidates[int(stable_hash({"seed": seed})[:8], 16) % len(candidates)]


def build_response_strategy(message, memory=None):
    profile = memory.get("context_profile") if isinstance(memory, dict) else {}
    profile = profile if isinstance(profile, dict) else {}
    primary_intent = detect_primary_intent(message)
    previous_style = profile.get("last_style_used") or profile.get("_last_output_style")
    previous_angle = profile.get("last_angle_used") or profile.get("_last_strategic_angle")
    previous_output_type = profile.get("last_output_type")
    previous_lens = profile.get("last_cognitive_lens")
    diversity_counter = safe_int(profile.get("response_diversity_counter"), 0)
    cognitive_lens = _select_cognitive_lens(primary_intent, previous_lens, diversity_counter, message)
    output_style = _style_for_lens(cognitive_lens, previous_style, diversity_counter, message)
    strategic_angle = _rotate_choice(
        STRATEGIC_ANGLES,
        previous_angle,
        f"{message}:{primary_intent}:{cognitive_lens}:{diversity_counter}:angle",
    )
    score_requested = "score" in (message or "").lower()

    return {
        "primary_intent": primary_intent,
        "cognitive_lens": cognitive_lens,
        "strategic_angle": strategic_angle,
        "output_style": output_style,
        "previous_output_style": previous_style,
        "previous_strategic_angle": previous_angle,
        "previous_cognitive_lens": previous_lens,
        "previous_output_type": previous_output_type,
        "diversity_counter": diversity_counter,
        "score_policy": "allowed_if_useful" if score_requested else "avoid_score",
        "cashflow_policy": (
            "allowed"
            if any(word in (message or "").lower() for word in ["cashflow", "budget", "charge", "liquidite", "tresorerie"])
            else "do_not_default_to_cashflow"
        ),
    }
