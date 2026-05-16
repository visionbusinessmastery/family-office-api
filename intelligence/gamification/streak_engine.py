from datetime import date, datetime


def update_streak(last_login_date, current_streak):

    today = date.today()

    # =========================
    # SAFE PARSING (DB COMPAT)
    # =========================
    if isinstance(last_login_date, str):
        try:
            last_login_date = datetime.strptime(last_login_date, "%Y-%m-%d").date()
        except Exception:
            last_login_date = None

    if not last_login_date:
        return 1  # first login

    # =========================
    # SAME DAY LOGIN
    # =========================
    if last_login_date == today:
        return current_streak

    # =========================
    # CONTINUOUS STREAK (+1 DAY)
    # =========================
    if (today - last_login_date).days == 1:
        return current_streak + 1

    # =========================
    # MISSED DAY → RESET
    # =========================
    return 0

def update_streak(last_login_date, current_streak, freeze=False):

    today = date.today()

    if freeze:
        return current_streak

    if isinstance(last_login_date, str):
        try:
            last_login_date = datetime.strptime(last_login_date, "%Y-%m-%d").date()
        except:
            last_login_date = None

    if not last_login_date:
        return 1

    if last_login_date == today:
        return current_streak

    if (today - last_login_date).days == 1:
        return current_streak + 1

    return 0
