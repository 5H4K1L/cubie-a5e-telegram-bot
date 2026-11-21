# AI feature design — Gemini

This document defines the approved AI scope for the Cubie A5E Telegram bot.

## Approved configuration

- Provider: Google Gemini API
- Reporting cadence: daily, weekly, and monthly
- Report language: English
- Permissions: read-only analysis
- Time zone: Asia/Dhaka (configurable)
- AI is an optional subsystem. If Gemini is unavailable, normal router commands, monitoring, and non-AI alerts must continue working.

## Responsibilities

The AI subsystem is split into independent modules:

```text
modules/
  ai/
    __init__.py
    gemini_client.py       # Gemini API adapter and timeouts
    ai_assistant.py        # Owner-only /ask command
    daily_summary.py       # Daily report generation
    weekly_summary.py      # Weekly report generation
    monthly_summary.py     # Monthly report generation
    log_analyzer.py        # Bounded, redacted log analysis
    recommendations.py     # Read-only troubleshooting suggestions
    prompts.py             # System instructions and report templates
```

The scheduler must run each report independently and prevent one failed report from stopping other scheduled tasks.

## Reporting and history

- Daily: summarize the previous local calendar day.
- Weekly: summarize the previous Monday–Sunday period.
- Monthly: summarize the previous calendar month.
- Send reports in English to the configured Telegram chat.
- Persist compact, timestamped metric snapshots and report-period boundaries locally (SQLite is preferred).
- Weekly and monthly reports must use stored historical snapshots, not pretend that current counters describe an entire past period.
- Store traffic counter deltas with interface identity and counter-reset detection. Do not label router interface counters as ISP monthly usage unless the source actually provides that measurement.
- Make report times and retention configurable. Use Asia/Dhaka by default.

## Data sent to Gemini

Send only the minimum data needed for the requested analysis: aggregate CPU, memory, storage, temperature, uptime, interface traffic deltas, connectivity checks, service states, and carefully selected/redacted log excerpts.

Never send Telegram tokens, Gemini API keys, passwords, Wi-Fi credentials, private keys, full configuration files, client MAC/IP inventories, or unredacted logs. Do not upload full router logs by default.

## Read-only security boundary

The AI provider must have no router command-execution tool and no ability to change UCI settings, firewall rules, DNS, packages, services, or reboot the device. Treat model output as untrusted text. Recommendations are informational and must not be executed automatically.

Only the configured Telegram owner may use AI commands or receive private reports. Apply request timeouts, bounded input/output sizes, rate limits, and graceful handling for missing keys, quota errors, network failures, and invalid responses.

## Configuration (example names)

Keep secrets in a local, untracked configuration file or protected environment file:

- `GEMINI_API_KEY` — private API key
- `GEMINI_MODEL` — model identifier, configurable rather than hard-coded
- `AI_ENABLED` — optional feature switch
- `AI_REPORT_CHAT_ID` — Telegram destination
- `AI_DAILY_REPORT_TIME`, `AI_WEEKLY_REPORT_DAY`, `AI_WEEKLY_REPORT_TIME`, `AI_MONTHLY_REPORT_DAY`, `AI_MONTHLY_REPORT_TIME`
- `TIMEZONE=Asia/Dhaka`

Never commit real API keys or bot tokens. Add all local secret files and databases to `.gitignore`.

## Dependency

Use Google's current official Python SDK, `google-genai` (imported as `from google import genai`). Pin and test a compatible version in the release requirements. Do not use the deprecated `google-generativeai` package for new implementation.

## Installation tutorial requirements

The installation guide must explain how to:
1. Create a Gemini API key in Google AI Studio.
2. Configure it locally without putting it in Git or shell history.
3. Set the model and report schedule.
4. Enable or disable AI independently from the base bot.
5. Verify the API connection with a safe test command.
6. Verify daily, weekly, and monthly scheduler jobs and inspect logs.
7. Understand that Gemini API quotas, model availability, and pricing depend on the account and selected model.

The actual install commands and package names must be validated against the released installer and both APK- and opkg-based firmware before the guide is marked production-ready.
