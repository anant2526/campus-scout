# 🎓 Campus Alert Agent

> **Automated monitoring for Anthropic Claude Campus Program opportunities.**
> Runs on GitHub Actions — works even when your laptop is off.

---

## 🏗️ Architecture

```
campus_alert_agent/
├── .github/
│   └── workflows/
│       └── ambassador-check.yml    ← GitHub Actions cron workflow
├── src/
│   ├── main.py                     ← Entry point (single-run batch job)
│   ├── checker.py                  ← Web scraping + Gemini AI analysis
│   ├── notifier.py                 ← Email / Telegram / Slack alerts
│   ├── storage.py                  ← Persistent duplicate detection (JSON)
│   └── config.py                   ← Configuration from environment
├── logs/
│   └── run.log                     ← Structured log file (uploaded as artifact)
├── requirements.txt
├── seen_results.json               ← Persisted state (committed to repo)
└── README.md
```

---

## ⏰ How the Schedule Works

The agent runs automatically via GitHub Actions cron:

```yaml
cron: "0 */8 * * *"
```

| Run | UTC Time | IST Time |
|-----|----------|----------|
| 1   | 00:00    | 05:30    |
| 2   | 08:00    | 13:30    |
| 3   | 16:00    | 21:30    |

**3 runs per day, every 8 hours, fully automated.**

### Changing the Schedule

Edit `.github/workflows/ambassador-check.yml` and modify the cron expression:

| Desired Schedule | Cron Expression |
|------------------|-----------------|
| Every 8 hours (default) | `0 */8 * * *` |
| Every 6 hours | `0 */6 * * *` |
| Every 4 hours | `0 */4 * * *` |
| Once a day (midnight) | `0 0 * * *` |
| Twice a day (9AM, 9PM) | `0 9,21 * * *` |

---

## 🔑 Setting Up Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Add these secrets:

| Secret Name | Description | How to Get |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | [AI Studio](https://aistudio.google.com/app/apikey) |
| `ALERT_EMAIL_TO` | Email to receive alerts | Your Gmail address |
| `ALERT_EMAIL_FROM` | Email to send from | Same or different Gmail |
| `GMAIL_APP_PASSWORD` | Gmail App Password (**not** your regular password) | [Google App Passwords](https://myaccount.google.com/apppasswords) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Create via [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Your Telegram user ID | Message [@userinfobot](https://t.me/userinfobot) |
| `SLACK_WEBHOOK_URL` | *(Optional)* Slack incoming webhook URL | [Slack API](https://api.slack.com/messaging/webhooks) |

> **⚠️ Important:** Telegram Chat ID must be YOUR personal user ID, not the bot's ID. The bot's ID is the number before the colon in the token — that's NOT your chat ID.

---

## 🚀 Manual Trigger

You can trigger the agent manually at any time:

1. Go to your repo on GitHub
2. Click the **Actions** tab
3. Select **Campus Alert Agent** from the left sidebar
4. Click **Run workflow** → **Run workflow**

---

## 🔄 How Duplicate Detection Works

```
Source URL scraped → Content hashed (SHA-256)
                         ↓
              Is this hash in seen_results.json?
                    ↙              ↘
                 YES                NO
              (skip it)     → Analyze with Gemini
                                    ↓
                             Opportunity detected?
                                ↙        ↘
                              YES         NO
                          Send alerts   Mark as seen
                          Mark as seen
```

- State is stored in `seen_results.json` at the repo root.
- After each run, the workflow commits the updated file back to the repo.
- Commits use `[skip ci]` suffix to avoid triggering recursive workflows.
- If the JSON file gets corrupted, it's automatically backed up and a fresh one is created.

---

## 📋 Logs

- **Live logs**: Visible in the GitHub Actions run output.
- **Persistent logs**: Uploaded as a workflow artifact after each run (kept for 30 days).
- **Location**: `logs/run.log`

To view logs:
1. Go to **Actions** tab
2. Click on a specific run
3. Scroll to **Artifacts** at the bottom
4. Download `agent-logs-XXXXX`

---

## 🛡️ Reliability Features

| Feature | Implementation |
|---|---|
| **Retry with backoff** | Scraping + Gemini calls retry 3× with exponential backoff |
| **Timeout protection** | 50-min internal Python timeout + 60-min GitHub Actions hard kill |
| **Atomic writes** | JSON state saved via temp-file-then-rename to prevent corruption |
| **Corruption recovery** | Corrupted JSON is backed up and a fresh state is started |
| **Independent channels** | Email/Telegram/Slack fail independently — one broken channel won't block others |
| **Idempotent reruns** | Re-running the same workflow won't send duplicate alerts |

---

## 🖥️ Local Development

For local testing, create a `.env` file:

```bash
GEMINI_API_KEY=your_key_here
ALERT_EMAIL_TO=you@gmail.com
ALERT_EMAIL_FROM=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=your_user_id
```

Then run:

```bash
pip install -r requirements.txt
python src/main.py
```

---

## 📦 Deployment

Push to GitHub and it's live:

```bash
git add .
git commit -m "Deploy campus alert agent"
git push origin main
```

The first automatic run will happen at the next 8-hour boundary (00:00, 08:00, or 16:00 UTC).

---

## 📜 License

MIT
