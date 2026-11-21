# Installation guide — ImmortalWrt and OpenWrt

This is an initial source release. Test on a system where you have recovery access. The installer installs firmware-matched Python packages, creates an isolated Python environment, and registers a procd service.

## 1. Requirements

- Radxa Cubie A5E with ImmortalWrt or OpenWrt, ARM64.
- Python 3.10 or newer, Git, pip, Python venv support, and SQLite Python bindings.
- SSH root access and working outbound DNS/HTTPS.
- Telegram bot token and your numeric Telegram user ID.
- Recommended: writable persistent storage for /opt and /etc/cubie-a5e-telegram-bot.
- Optional: Google Gemini API key.

The 1 GB RAM model is supported by design. AI is disabled by default; the Gemini SDK is not installed by the base installer.

## 2. Inspect firmware and package manager

    cat /etc/openwrt_release 2>/dev/null || cat /etc/os-release
    uname -m
    free -h 2>/dev/null || cat /proc/meminfo | head
    df -h
    command -v apk && apk --version
    command -v opkg && opkg --version
    python3 --version

Use only feeds matching the installed firmware release, target, and architecture. Do not mix Cortex-A53/Cortex-A55 or different release feeds.

## 3. Prerequisites installed by the script

For APK-based ImmortalWrt, the installer uses these package names:

- `python3`
- `python3-venv`
- `python3-pip`
- `python3-sqlite3`
- `git`
- `ca-bundle`

For opkg-based systems, the script requests the corresponding package names. Package availability can vary by firmware build. The script checks Python imports for sqlite3, zoneinfo, ssl, and venv before continuing.

On the tested Cubie A5E package feeds, the correct names are `python3-pip` and `python3-venv` — not `py3-pip` or `py3-virtualenv`.

## 4. Clone and install

    cd /root
    git clone https://github.com/5H4K1L/cubie-a5e-telegram-bot.git
    cd cubie-a5e-telegram-bot
    sh install.sh

The installer places the application in /opt/cubie-a5e-telegram-bot, creates a Python virtual environment, installs base dependencies, creates a private .env template, and registers /etc/init.d/cubie-a5e-telegram-bot. It enables boot startup but does not start the bot automatically during installation.

If installation fails, resolve the reported package/dependency issue before continuing. Do not force packages from another release or architecture.

## 5. Configure Telegram

Edit /opt/cubie-a5e-telegram-bot/.env and set:

    TELEGRAM_BOT_TOKEN=your_new_bot_token
    TELEGRAM_OWNER_ID=your_numeric_telegram_user_id
    TIMEZONE=Asia/Dhaka

Protect the file:

    chmod 600 /opt/cubie-a5e-telegram-bot/.env

Create a bot through @BotFather. Obtain your numeric user ID from a trusted Telegram ID tool. Never commit the token. If a token was exposed, revoke it with BotFather and issue a replacement.

## 6. Select WAN interface

Check the default route:

    ip -4 route show default

For this router's reported default route, use:

    WAN_INTERFACE=pppoe-wan

Set this in .env. WAN RX is treated as download and WAN TX as upload. If the WAN device changes later, update this setting.

## 7. Start and enable procd

The installer enables the service for boot. After configuring .env, run:

    /etc/init.d/cubie-a5e-telegram-bot start
    /etc/init.d/cubie-a5e-telegram-bot status
    logread -e cubie

The bot loads .env by its absolute location beside bot.py, so it does not depend on procd's working directory. The service restarts if the process exits. The bot sends a startup notification to the configured owner.

Stop or restart:

    /etc/init.d/cubie-a5e-telegram-bot stop
    /etc/init.d/cubie-a5e-telegram-bot restart

## 8. Telegram commands

All commands are owner-only:
- /start, /help
- /status
- /cpu, /memory, /storage, /temp, /uptime
- /network
- /clients — DHCP leases only; not every statically configured or Wi-Fi client.
- /system
- /traffic — takes a sample and displays month-to-date totals.
- /traffic_today — previous local calendar day.
- /traffic_month — previous calendar month.
- /traffic_mtd — current month to date.
- /traffic_reset — requires confirmation and deletes local traffic history.
- /ai — optional Gemini read-only report.
- /reboot — requires confirmation.

## 9. Traffic reports

The bot samples WAN counters every 60 seconds and stores snapshots/deltas in SQLite at /etc/cubie-a5e-telegram-bot/traffic.sqlite3.

- Daily report: previous local day at DAILY_REPORT_TIME (default 08:00).
- Monthly report: previous calendar month, sent on day 1 at MONTHLY_REPORT_TIME (default 08:05).

The first sample establishes a baseline. Gaps longer than five minutes, counter decreases, and WAN-interface changes make affected periods incomplete. Pre-installation traffic cannot be reconstructed. These router counters may differ from ISP billing totals. See docs/TRAFFIC_ACCOUNTING.md.

## 10. Optional Gemini AI

AI is disabled by default and not required for normal operation.

Install the optional SDK:

    cd /opt/cubie-a5e-telegram-bot
    .venv/bin/python -m pip install -r requirements-ai.txt

Set in .env:

    AI_ENABLED=true
    GEMINI_API_KEY=your_private_key
    GEMINI_MODEL=gemini-2.5-flash
    AI_DAILY_TIME=08:15
    AI_WEEKLY_DAY=0
    AI_WEEKLY_TIME=08:20
    AI_MONTHLY_DAY=1
    AI_MONTHLY_TIME=08:25

Restart the service. Weekly day uses Monday=0 through Sunday=6; monthly day is 1–31. AI receives aggregate metrics only and cannot execute router commands. Missing keys, SDK errors, and Gemini outages do not stop normal bot functions.

See https://ai.google.dev/gemini-api/docs for current model access, quotas, and pricing.

## 11. Alerts

Default thresholds: temperature 80 °C, RAM 90%, root filesystem 90%. Configure TEMPERATURE_ALERT_C, MEMORY_ALERT_PERCENT, and DISK_ALERT_PERCENT in .env. Alert cooldown is 30 minutes per alert type.

## 12. Tests

On a development machine with Python 3.10+:

    python3 -m unittest discover -s tests -v

GitHub Actions runs tests on pushes and pull requests.

## 13. Updating and backups

Back up the private configuration and traffic database before updating:

    cp /opt/cubie-a5e-telegram-bot/.env /root/cubie-bot.env.backup
    cp /etc/cubie-a5e-telegram-bot/traffic.sqlite3 /root/traffic.sqlite3.backup 2>/dev/null || true

Stop the service, update source with a reviewed Git pull, install changed requirements, and restart. Preserve .env and the SQLite database.

## 14. Uninstall

    /etc/init.d/cubie-a5e-telegram-bot stop
    /etc/init.d/cubie-a5e-telegram-bot disable
    rm -f /etc/init.d/cubie-a5e-telegram-bot

Remove /opt/cubie-a5e-telegram-bot only if you no longer need source or local .env. Remove /etc/cubie-a5e-telegram-bot only if you deliberately want to delete traffic history.

## Troubleshooting

- Package not found: verify release, target, architecture, and feed configuration.
- Python venv failure: verify that python3-venv for the exact firmware is installed.
- Bot unauthorized: verify TELEGRAM_OWNER_ID is the numeric ID of the account sending commands.
- No response: verify token, outbound DNS/HTTPS, and process state.
- No WAN reports: verify WAN_INTERFACE, default route, system time, and SQLite write permissions.
- Incomplete usage: expected after install, reboot gaps, counter resets, or interface changes; data is not fabricated.
- Gemini failure: check optional SDK, API key, model availability, and quota.
- Service fails: inspect logread -e cubie, executable paths, .env permissions, and disk space.
