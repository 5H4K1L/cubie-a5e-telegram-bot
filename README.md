# Cubie A5E Telegram Bot

A modular Python Telegram bot for monitoring a Radxa Cubie A5E running ImmortalWrt or OpenWrt (ARM64).

## Features

- Owner-only Telegram commands and private notifications.
- Router status, CPU load, RAM, root storage, thermal sensors, uptime, firmware/kernel details.
- Network interfaces, default WAN detection, and DHCP lease listing.
- Persistent SQLite WAN accounting: daily, previous-month, and month-to-date download/upload reports.
- Detects counter decreases, WAN-interface changes, and long sampling gaps; affected reports are marked incomplete.
- Automatic temperature, memory, and storage threshold alerts.
- Optional Google Gemini read-only health reports (daily, weekly, monthly) and on-demand /ai analysis.
- procd service for automatic startup.
- APK- and opkg-based firmware support, subject to Python/package availability.

## Repository status

The initial complete bot source, traffic accounting, tests, example configuration, installer, and procd service are published. This is an initial release candidate: test it on a system where you have recovery access. Python package availability and writable storage vary across firmware builds.

## Quick start

1. Create a Telegram bot with @BotFather and obtain your numeric Telegram user ID.
2. SSH into the router as root.
3. Check that Python 3.10+, Git, pip, and virtual-environment support are available.
4. Clone and run:

    git clone https://github.com/5H4K1L/cubie-a5e-telegram-bot.git
    cd cubie-a5e-telegram-bot
    sh install.sh

5. Edit /opt/cubie-a5e-telegram-bot/.env, set TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID, then start:

    /etc/init.d/cubie-a5e-telegram-bot start

Read INSTALL.md before installation.

## Commands

| Command | Function |
|---|---|
| /start, /help | Help |
| /status | Overall router status |
| /cpu, /memory, /storage, /temp, /uptime | Resource information |
| /network | Interfaces and WAN |
| /clients | DHCP leases (not a complete Wi-Fi inventory) |
| /system | Firmware, board, kernel, architecture |
| /traffic | Record a sample and show month-to-date usage |
| /traffic_today | Previous local calendar day |
| /traffic_month | Previous calendar month |
| /traffic_mtd | Current month to date |
| /traffic_reset | Owner-confirmed deletion of local usage history |
| /ai | Optional read-only Gemini analysis |
| /reboot | Owner-confirmed router reboot |

All commands and confirmation callbacks are restricted to the numeric Telegram owner ID.

## Configuration

Set TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID in the private .env file. Set WAN_INTERFACE if automatic default-route detection selects the wrong device (for example pppoe-wan). Default timezone is Asia/Dhaka.

### Optional Gemini AI

AI is disabled by default. Install the extra dependency only if needed:

    cd /opt/cubie-a5e-telegram-bot
    .venv/bin/pip install -r requirements-ai.txt

Then set AI_ENABLED=true and GEMINI_API_KEY in .env. The AI receives aggregate/redacted metrics only and has no command-execution capability. Gemini failures do not interrupt normal monitoring.

## WAN usage limitations

Traffic totals are measured from the selected Linux WAN interface RX/TX counters. They are router-side measurements and may differ from ISP billing totals. Sampling starts when the bot is installed; no pre-installation usage is reconstructed. Counter resets, interface changes, and missing intervals are reported as incomplete. See docs/TRAFFIC_ACCOUNTING.md.

## Security

- Never commit .env, bot tokens, Gemini keys, passwords, Wi-Fi credentials, or private keys.
- .gitignore excludes local secrets and runtime databases.
- The AI subsystem is read-only.
- Reboot and traffic-history deletion require explicit confirmation.
- The bot runs with router privileges for telemetry and reboot access; protect SSH access.

## Development and tests

    python3 -m unittest discover -s tests -v

See GitHub Actions for automated test runs.
