# AI feature — Gemini

## Implemented behavior

The optional AI subsystem uses Google's official google-genai Python SDK. It provides an on-demand /ai analysis and scheduled daily, weekly, and monthly read-only health summaries. Each scheduled report analyzes an aggregate router snapshot at that time; it does not claim to have historical weekly/monthly measurements.

- Provider: Google Gemini API.
- Language: English.
- Time zone: Asia/Dhaka by default; configurable.
- AI disabled by default and separated from core dependencies.
- Missing keys, SDK errors, and API failures do not interrupt ordinary router monitoring or traffic reports.

## Modules

    modules/ai/
      __init__.py
      gemini_client.py
      ai_assistant.py

The Gemini client receives only sanitized telemetry. It has no router shell, UCI, service-control, package-management, or reboot tools.

## Data sent to Gemini

Only aggregate selected fields are sent:
- Hostname, kernel, architecture, and WAN interface name.
- Uptime and load averages.
- Total/used memory and root filesystem usage.
- Highest available thermal-zone reading.
- Interface count and DHCP lease count only (no MAC/IP/hostname list).

Never send Telegram bot tokens, Gemini keys, passwords, Wi-Fi credentials, private keys, full router configuration, client inventories, or raw/unredacted logs. Treat AI output as untrusted advice. No AI output is executed.

## Enable Gemini

Install the optional SDK:

    cd /opt/cubie-a5e-telegram-bot
    .venv/bin/pip install -r requirements-ai.txt

Set in the private .env:

    AI_ENABLED=true
    GEMINI_API_KEY=your_private_key
    GEMINI_MODEL=gemini-2.5-flash
    AI_DAILY_TIME=08:15
    AI_WEEKLY_DAY=0
    AI_WEEKLY_TIME=08:20
    AI_MONTHLY_DAY=1
    AI_MONTHLY_TIME=08:25
    TIMEZONE=Asia/Dhaka

Restart the service. Weekly day uses Monday=0 through Sunday=6. Monthly day must be 1–31. Check model access, quotas, and pricing in https://ai.google.dev/gemini-api/docs.

## Traffic accounting is separate

Daily and monthly WAN usage totals are calculated locally from interface counters and SQLite history. Gemini does not calculate or invent factual totals. The bot still sends usage reports if Gemini is disabled or unavailable. Router interface totals may differ from ISP billing.

See docs/TRAFFIC_ACCOUNTING.md and INSTALL.md.
