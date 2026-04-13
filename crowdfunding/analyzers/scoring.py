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

def global_score(return_rate, risk, duration):
    score = 0

    score += return_rate * 2

    if risk == "low":
        score += 20
    elif risk == "medium":
        score += 10

    if duration < 24:
        score += 10

    return min(score, 100)
