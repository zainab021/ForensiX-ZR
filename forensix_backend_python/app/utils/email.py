import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "ForensiX ZR Unit")


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email over SMTP. Returns False (and logs) instead of
    raising if SMTP isn't configured, so callers can degrade gracefully rather
    than crashing a request when email credentials are missing in dev."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[email] SMTP not configured — skipping email to {to}: {subject}")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
    message["To"] = to
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        print(f"[email] Failed to send email to {to}: {exc}")
        return False


def send_otp_email(to: str, otp: str) -> bool:
    subject = "ForensiX ZR Unit — Password Reset Code"
    body = (
        f"Your password reset code is: {otp}\n\n"
        "This code expires in 10 minutes. If you did not request a password "
        "reset, you can safely ignore this email."
    )
    return send_email(to, subject, body)
