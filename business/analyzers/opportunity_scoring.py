def score_opportunity(item, mode):

    score = 0

    if mode == "create":
        score += 30

    if mode == "grow":
        score += 20

    if mode == "buy":
        score += 40

    return score
