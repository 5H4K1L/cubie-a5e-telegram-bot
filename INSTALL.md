# Installation guide

> **Development status:** The public repository is being prepared. The modular bot source, installer, and procd service must be published and tested before this guide can be treated as a release-ready procedure. Do not run guessed install commands or copy an installer from an unofficial fork. This document records the supported setup flow and approved configuration.

## 1. Prerequisites

- Radxa Cubie A5E (1 GB RAM or higher recommended).
- ImmortalWrt or OpenWrt.
- SSH access with root privileges.
- Working internet connection.
- Telegram account and a bot created with [@BotFather](https://t.me/BotFather).
- Telegram numeric user ID for owner-only access.
- Optional: Google Gemini API key from [Google AI Studio](https://aistudio.google.com/).

The target is ARM64, including Cortex-A53 and Cortex-A55. Package availability depends on the firmware release, target, architecture, and configured feeds.

## 2. Inspect the router before installing

Connect over SSH and run:

```sh
cat /etc/openwrt_release 2>/dev/null || cat /etc/os-release
uname -m
opkg --version 2>/dev/null || apk --version
df -h
free -h 2>/dev/null || cat /proc/meminfo | head
python3 --version 2>/dev/null || echo "Python 3 is not installed"
```

Confirm that the configured package feeds match the installed firmware release and target. Do not mix packages from different OpenWrt/ImmortalWrt releases or CPU targets.

## 3. Install prerequisites

Use the package manager supplied by the firmware. Refresh its package index first:

- APK-based firmware: `apk update`
- opkg-based firmware: `opkg update`

Install Git, Python 3, certificates, and the Python packaging/virtual-environment components available for that exact firmware release. Package names differ between releases; check availability before installing:

- APK: `apk search python3`
- opkg: `opkg list | grep -E '^(python3|python3-pip|python3-venv|git|ca-bundle) '`

Do not force-install packages from another target or release. If a supported Python virtual environment cannot be created on the router, use the project's documented isolated-dependency method for that release.

## 4. Download the project

After the first source-code release is published:

```sh
cd /root
git clone https://github.com/5H4K1L/cubie-a5e-telegram-bot.git
cd cubie-a5e-telegram-bot
```

For a later update, use the project's update instructions and preserve the local configuration and database.

## 5. Configure Telegram

1. Open [@BotFather](https://t.me/BotFather) in Telegram.
2. Create a bot with `/newbot`.
3. Copy the bot token and keep it private.
4. Obtain your own numeric Telegram user ID using a trusted ID helper bot or the project's documented method.
5. Configure the token, owner ID, and report chat ID in the local configuration file described by the release.

Never paste a bot token into a public issue, source file, screenshot, or Git commit. If a token is exposed, revoke it with BotFather and generate a replacement.

## 6. Configure Gemini AI (optional)

The approved AI defaults are:

- Provider: Google Gemini API.
- Reports: daily, weekly, and monthly.
- Language: English.
- Permissions: read-only.
- Time zone: Asia/Dhaka (configurable).

Create an API key in [Google AI Studio](https://aistudio.google.com/). Store it in the private local configuration or protected environment file supported by the release. Do not put the key in `config.example.json`, source code, shell command history, or Git.

Configure the model identifier and report schedule using the release's example configuration. Model availability, quota, and pricing vary by account and model; check the current [Gemini API documentation](https://ai.google.dev/gemini-api/docs) and [pricing](https://ai.google.dev/gemini-api/docs/pricing).

The AI subsystem uses Google's `google-genai` Python SDK. AI is optional: missing API credentials or Gemini outages must not stop normal router monitoring and Telegram commands.

### AI privacy and permissions

Only minimum aggregate router metrics and selected redacted log excerpts may be sent to Gemini. Never send passwords, API keys, bot tokens, Wi-Fi credentials, private keys, full configuration files, or unredacted logs. The AI has no command-execution capability and cannot change router settings, firewall, DNS, services, packages, or reboot the device. Its output is advice only.

## 7. Install and enable the background service

The release will provide an ImmortalWrt/OpenWrt procd init script and installer. Use the exact commands documented by that release to install the service, enable it at boot, and start it. Do not manually invent service paths or copy an init script from a different release.

After installation, verify the service state and inspect its log using the service name and log path specified by the release. The bot should restart after a router reboot.

## 8. Internet usage reports

The bot is designed to send separate daily and monthly WAN usage summaries.

- Daily report: previous local calendar day's download and upload totals.
- Monthly report: previous calendar month's totals, with month-to-date usage available on demand.
- Reports must identify the WAN interface and date range.
- Usage is calculated from locally stored interface-counter snapshots. If the router reboots, counters reset, or the WAN interface changes, the bot must detect the discontinuity and mark affected totals as incomplete rather than inventing data.
- These are router-measured estimates and may differ from ISP billing totals.
- Historical reporting starts only after the bot has collected enough baseline data; it cannot reconstruct usage from before installation.

## 9. Verify the bot

Use the release's documented test commands to verify:

- Telegram connection and owner authorization.
- Router status, temperature, memory, storage, uptime, and network commands.
- Internet and service monitoring.
- Notification delivery.
- Gemini connection (if enabled).
- Daily, weekly, and monthly report scheduling.
- Recovery when Gemini is unreachable: ordinary bot functions must continue.

## 9. Updating

Before updating, back up the private configuration and local history database. Fetch the new source using the release's update procedure. Do not overwrite local secrets or delete report history unless the release notes explicitly require a migration.

## 10. Uninstalling

Use the release's uninstall procedure to stop and disable the procd service, remove the application files and virtual environment, and optionally retain or remove the configuration, logs, and SQLite history database. The uninstall procedure must clearly distinguish application files from user data.

## 11. Troubleshooting checklist

- **Package not found:** confirm firmware release, target, architecture, and feed URLs.
- **Python import error:** verify the project's virtual environment and pinned dependencies.
- **Bot does not respond:** check token validity, outbound DNS/HTTPS, Telegram connectivity, and owner ID.
- **Service does not start:** inspect procd status and the application log; verify file paths and permissions.
- **Gemini authentication failure:** check the local API key and selected model.
- **Gemini quota/rate limit:** check AI Studio usage and current account limits; normal bot functions should remain available.
- **No scheduled report:** check router time synchronization, configured time zone, scheduler logs, and report destination.
- **Storage pressure:** check log/database retention and available writable space before increasing history retention.

## 12. Security checklist

- Keep bot and Gemini credentials outside Git.
- Restrict local configuration permissions (for example, mode `0600`).
- Keep owner-only command authorization enabled.
- Do not expose the bot's control interface to unauthenticated users.
- Keep AI read-only.
- Back up configuration and report history before upgrades.
- Rotate any credential that has been exposed.

---

When the first complete source release is published, this guide must be updated with exact installer commands, supported package names for tested APK/opkg firmware versions, service-management commands, and verified screenshots/output. Until then, this is the setup plan, not a claim that the installer is already available.
