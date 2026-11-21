# Cubie A5E Telegram Bot

A modular Python Telegram bot project for monitoring a Radxa Cubie A5E running ImmortalWrt or OpenWrt.

> **Development status:** The repository currently contains project documentation and design specifications. The complete bot source, tested installer, and procd service have not yet been published. Do not treat this repository as an installable release yet.

## Project goals

- Separate Python module for each router feature so individual features can be fixed independently.
- Owner-restricted Telegram commands and notifications.
- Router status, CPU temperature, memory, storage, uptime, network, traffic, clients, and service monitoring.
- Daily and monthly WAN download/upload usage reports based on locally stored counter snapshots.
- Optional Gemini-powered AI summaries and troubleshooting advice.
- procd service for automatic startup on OpenWrt/ImmortalWrt.
- No secrets committed to the public repository.

## AI configuration

The approved AI design uses Google Gemini, English reports, daily/weekly/monthly summaries, and read-only permissions. AI failures must not interrupt ordinary router monitoring.

## Documentation

- [Installation guide](INSTALL.md) — prerequisites and the planned installation/configuration flow.
- [AI design](docs/AI_DESIGN.md) — Gemini architecture, reporting periods, privacy, and read-only security boundary.

The installation guide will be finalized with exact commands after the source and installer are implemented and tested on APK- and opkg-based firmware.

## Security

Never commit Telegram bot tokens, Gemini API keys, passwords, Wi-Fi credentials, or private router configuration. See [GitHub secret scanning guidance](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning).
