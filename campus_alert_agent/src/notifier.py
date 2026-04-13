"""
Notification module — sends alerts via Email, Telegram, and Slack.

DESIGN: Each notification channel is independent. If one fails,
the others still fire. This prevents a broken Telegram config
from blocking email delivery, etc.

Preserved the original alerter.py email + Telegram logic.
Added Slack webhook support.
"""
import smtplib
import logging
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

import config


def _get_ist_timestamp() -> str:
    """Generate the current IST timestamp string."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist_tz).strftime("%Y-%m-%d %H:%M:%S IST")


# ══════════════════════════════════════════════════════════════════════════
# EMAIL (Gmail SMTP)
# ══════════════════════════════════════════════════════════════════════════

def send_email_alert(url: str, summary: str, excerpt: str) -> None:
    """Send an email alert using Gmail SMTP."""
    if not all([config.ALERT_EMAIL_FROM, config.GMAIL_APP_PASSWORD, config.ALERT_EMAIL_TO]):
        logging.warning("Email credentials not configured — skipping email alert.")
        return

    timestamp_ist = _get_ist_timestamp()

    msg = MIMEMultipart()
    msg["From"] = config.ALERT_EMAIL_FROM
    msg["To"] = config.ALERT_EMAIL_TO
    msg["Subject"] = "🚨 CAMPUS ALERT: Anthropic Claude Campus Program detected!"

    body = (
        f"Campus Alert Agent detected a relevant announcement!\n\n"
        f"URL: {url}\n\n"
        f"Summary: {summary}\n\n"
        f"Relevant excerpt:\n{excerpt}\n\n"
        f"Detected at: {timestamp_ist}\n\n"
        f"— Campus Alert Agent (GitHub Actions)"
    )
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    try:
        server.starttls()
        server.login(config.ALERT_EMAIL_FROM, config.GMAIL_APP_PASSWORD)
        server.send_message(msg)
        logging.info("✅ Email alert sent successfully.")
    finally:
        server.quit()


# ══════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════════════════

def send_telegram_alert(url: str, summary: str, excerpt: str) -> None:
    """Send an alert to Telegram."""
    if not all([config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID]):
        logging.warning("Telegram credentials not configured — skipping Telegram alert.")
        return

    timestamp_ist = _get_ist_timestamp()
    message = (
        f"🚨 *CAMPUS ALERT*\n\n"
        f"*URL:* {url}\n"
        f"*Summary:* {summary}\n"
        f"*Excerpt:* _{excerpt}_\n"
        f"*Time:* {timestamp_ist}"
    )

    endpoint = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "parse_mode": "Markdown",
        "text": message,
    }

    response = requests.post(endpoint, json=payload, timeout=10)
    if response.status_code == 200:
        logging.info("✅ Telegram alert sent successfully.")
    else:
        logging.warning(
            f"Telegram alert failed ({response.status_code}): {response.text}"
        )


# ══════════════════════════════════════════════════════════════════════════
# SLACK WEBHOOK
# ══════════════════════════════════════════════════════════════════════════

def send_slack_alert(url: str, summary: str, excerpt: str) -> None:
    """Send an alert to Slack via incoming webhook."""
    if not config.SLACK_WEBHOOK_URL:
        logging.info("Slack webhook not configured — skipping Slack alert.")
        return

    timestamp_ist = _get_ist_timestamp()
    payload = {
        "text": (
            f"🚨 *Campus Alert Agent*\n"
            f"*URL:* <{url}>\n"
            f"*Summary:* {summary}\n"
            f"*Excerpt:* {excerpt}\n"
            f"*Time:* {timestamp_ist}"
        )
    }

    response = requests.post(
        config.SLACK_WEBHOOK_URL, json=payload, timeout=10
    )
    if response.status_code == 200:
        logging.info("✅ Slack alert sent successfully.")
    else:
        logging.warning(
            f"Slack alert failed ({response.status_code}): {response.text}"
        )


# ══════════════════════════════════════════════════════════════════════════
# MASTER DISPATCHER
# ══════════════════════════════════════════════════════════════════════════

def send_alert(url: str, summary: str, excerpt: str) -> None:
    """
    Send alert via ALL configured channels.
    Each channel is independent — one failure doesn't block others.
    """
    channels = [
        ("Email", send_email_alert),
        ("Telegram", send_telegram_alert),
        ("Slack", send_slack_alert),
    ]

    for name, sender in channels:
        try:
            sender(url, summary, excerpt)
        except Exception as e:
            logging.error(f"Failed to send {name} alert: {e}")
