"""Gmail(SMTP)で HTML メールを送る."""
from __future__ import annotations

import os
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send(subject: str, html: str, plain: str) -> None:
    user = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]  # Google の「アプリ パスワード」(16 桁)
    to = [a.strip() for a in os.environ.get("MAIL_TO", user).split(",") if a.strip()]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg["From"] = user
    msg["To"] = ", ".join(to)
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(user, password)
        s.sendmail(user, to, msg.as_string())
