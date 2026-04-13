def score_project(project, risk_level):

    score = 0

    # rendement
    if project["expected_return"] > 10:
        score += 40
    elif project["expected_return"] > 6:
        score += 20

    # risque
    if risk_level == "low" and project["risk"] == "low":
        score += 30
    elif risk_level == "high":
        score += 20

    # durée
    if project["duration"] < 24:
        score += 30

    return score
