def score_opportunity(item, mode):

    score = 0

    if mode == "create":
        score += 30

    if mode == "grow":
        score += 20

    if mode == "buy":
        score += 40

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
