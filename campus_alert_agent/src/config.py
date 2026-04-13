"""
Configuration for Campus Alert Agent.

DESIGN: All sensitive values come from environment variables.
- In GitHub Actions: injected via secrets in the workflow YAML.
- Locally (for testing): use a .env file with python-dotenv.

We attempt to load dotenv if available, but don't require it.
This keeps the production path dependency-free while allowing
local development convenience.
"""
import os

# ── Attempt .env loading for local dev (optional dependency) ──────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Running in CI — dotenv not needed

# ── API Keys ──────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Email Configuration ──────────────────────────────────────────────────
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# ── Telegram Configuration ───────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Slack Configuration (optional) ───────────────────────────────────────
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# ── Gemini Model Settings ────────────────────────────────────────────────
GEMINI_MODEL = "gemini-1.5-flash"
MAX_TEXT_CHARS = 6000

# ── Sources to Monitor ───────────────────────────────────────────────────
# Add more Anthropic pages here as they appear.
SOURCES = [
    "https://www.anthropic.com/news",
    "https://www.anthropic.com/careers",
]

# ── Timeout ──────────────────────────────────────────────────────────────
# Internal Python timeout in seconds (50 min, leaving 10 min buffer
# before the GitHub Actions 60-min hard kill).
INTERNAL_TIMEOUT_SECONDS = 50 * 60

# ── Storage ──────────────────────────────────────────────────────────────
SEEN_RESULTS_FILE = "seen_results.json"
LOG_FILE = "logs/run.log"
