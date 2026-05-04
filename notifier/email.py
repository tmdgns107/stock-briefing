import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(report: str):
    sender = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]
    today = date.today().strftime("%Y-%m-%d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Stock Briefing] {today} 미국주식 일일 브리핑"
    msg["From"] = sender
    msg["To"] = recipient

    html = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 700px; margin: auto; padding: 20px;">
  <h2 style="color: #1a73e8;">📈 미국주식 일일 브리핑 — {today}</h2>
  <hr>
  {'<br>'.join(report.replace('###', '<h3>').replace('**', '<strong>').splitlines())}
  <hr>
  <p style="color: gray; font-size: 12px;">본 리포트는 투자 권유가 아닙니다. 참고용으로만 활용하세요.</p>
</body>
</html>
"""

    msg.attach(MIMEText(report, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    print(f"이메일 발송 완료: {recipient}")
