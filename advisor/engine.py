def detect_risk(message: str):
    try:
        value = float(message)
    except:
        value = 0.5

    if value < 0.3:
        return "low"
    elif value < 0.7:
        return "medium"
    return "high"


def extract_budget(message: str):
    return 1000
