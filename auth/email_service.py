import smtplib
import os
from email.mime.text import MIMEText

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")



# =========================
# SEND EMAIL VERIFICATION
# =========================
def send_verification_email(email: str, token: str):

    link = f"http://localhost:3000/verify-email?token={token}"

    msg = MIMEText(f"""
    Clique ici pour vérifier ton email :

    {link}
    """)

    msg["Subject"] = "Vérification de ton compte"
    msg["From"] = EMAIL_USER
    msg["To"] = email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
