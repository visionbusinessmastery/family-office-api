import re

from fastapi import HTTPException


MAX_PROMPT_CHARS = 4000

FORBIDDEN_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+les\s+instructions",
    r"system\s+prompt",
    r"montre.*prompt",
    r"show.*system",
    r"developer\s+message",
    r"chain\s+of\s+thought",
    r"raisonnement\s+interne",
    r"jailbreak",
    r"role\s*:\s*system",
]


def sanitize_advisor_prompt(message: str):
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", message or "").strip()
    cleaned = re.sub(r"\s{3,}", "  ", cleaned)
    return cleaned[:MAX_PROMPT_CHARS]


def inspect_advisor_prompt(message: str):
    cleaned = sanitize_advisor_prompt(message)
    lowered = cleaned.lower()

    if len(message or "") > MAX_PROMPT_CHARS:
        raise HTTPException(
            status_code=413,
            detail="Message trop long. Ethan peut t'aider plus efficacement avec une demande plus concise.",
        )

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, lowered):
            raise HTTPException(
                status_code=400,
                detail="Ethan reste concentre sur ton accompagnement patrimonial. Reformule ta question sans instruction systeme.",
            )

    repeated = re.search(r"(.{30,})\1{3,}", lowered)
    if repeated:
        raise HTTPException(
            status_code=400,
            detail="Message detecte comme repetitif. Reformule en une question claire.",
        )

    return cleaned
