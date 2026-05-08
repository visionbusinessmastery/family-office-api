from datetime import date

def update_streak(last_login_date, current_streak):

    today = date.today()

    if last_login_date == today:
        return current_streak

    if last_login_date and (today - last_login_date).days == 1:
        return current_streak + 1

    return 0
