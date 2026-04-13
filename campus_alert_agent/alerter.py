"""Alerting module for campus_alert_agent."""
import smtplib
import logging
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
import config

def get_ist_timestamp() -> str:
    """Generate the current IST timestamp string."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist_tz).strftime("%Y-%m-%d %H:%M:%S IST")

def send_email_alert(url: str, summary: str, excerpt: str) -> None:
    """Send an email alert using Gmail SMTP."""
    timestamp_ist = get_ist_timestamp()
    
    msg = MIMEMultipart()
    msg['From'] = config.ALERT_EMAIL_FROM
    msg['To'] = config.ALERT_EMAIL_TO
    msg['Subject'] = "CAMPUS ALERT: Anthropic Claude Campus Program detected!"
    
    body = f"Campus Alert Agent detected a relevant announcement!\n\nURL: {url}\n\nSummary: {summary}\n\nRelevant excerpt:\n{excerpt}\n\nDetected at: {timestamp_ist}"
    msg.attach(MIMEText(body, 'plain'))
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    try:
        server.starttls()
        server.login(config.ALERT_EMAIL_FROM, config.GMAIL_APP_PASSWORD)
        server.send_message(msg)
    finally:
        server.quit()

def send_telegram_alert(url: str, summary: str, excerpt: str) -> None:
    """Send an alert to Telegram."""
    timestamp_ist = get_ist_timestamp()
    message = f"*CAMPUS ALERT: Claude Campus Program Detected!*\n\n*URL:* {url}\n*Summary:* {summary}\n*Excerpt:* _{excerpt}_\n*Time:* {timestamp_ist}"
    
    endpoint = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "parse_mode": "Markdown",
        "text": message
    }
    
    response = requests.post(endpoint, json=payload, timeout=10)
    if response.status_code != 200:
        logging.warning(f"Telegram alert failed with status {response.status_code}: {response.text}")

def send_alert(url: str, summary: str, excerpt: str) -> None:
    """Master function to send both email and Telegram alerts."""
    try:
        send_email_alert(url, summary, excerpt)
        logging.info("Email alert sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email alert: {e}")
        
    try:
        send_telegram_alert(url, summary, excerpt)
        logging.info("Telegram alert sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send Telegram alert: {e}")
