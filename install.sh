#!/bin/sh
set -eu

APP_DIR="/opt/cubie-a5e-telegram-bot"
SERVICE="/etc/init.d/cubie-a5e-telegram-bot"
REPO_URL="https://github.com/5H4K1L/cubie-a5e-telegram-bot.git"

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this installer as root." >&2
    exit 1
fi

if command -v apk >/dev/null 2>&1; then
    PM="apk"
elif command -v opkg >/dev/null 2>&1; then
    PM="opkg"
else
    echo "Neither apk nor opkg found. Unsupported firmware/package manager." >&2
    exit 1
fi

echo "Installing firmware-matched Python and runtime prerequisites..."
if [ "$PM" = apk ]; then
    apk update
    apk add python3 python3-venv python3-pip python3-sqlite3 git ca-bundle
else
    opkg update
    opkg install python3 python3-pip python3-venv python3-sqlite3 git ca-bundle
fi

if [ ! -x /usr/bin/python3 ]; then
    echo "Python 3 was not installed at /usr/bin/python3." >&2
    exit 1
fi

python3 -c 'import sqlite3, zoneinfo, ssl, venv' || {
    echo "Python sqlite3, zoneinfo, TLS, and venv support are required." >&2
    exit 1
}
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || {
    echo "Python 3.10 or newer is required." >&2
    exit 1
}

if ! command -v git >/dev/null 2>&1; then
    echo "Git is required but was not installed." >&2
    exit 1
fi

if [ ! -d "$APP_DIR/.git" ]; then
    mkdir -p "$(dirname "$APP_DIR")"
    git clone "$REPO_URL" "$APP_DIR"
else
    git -C "$APP_DIR" pull --ff-only
fi

mkdir -p /etc/cubie-a5e-telegram-bot
cd "$APP_DIR"

if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
    python3 -m venv "$APP_DIR/.venv"
fi

"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/python" -m pip install -r requirements.txt

if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo "Created $APP_DIR/.env. Configure TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID before starting."
else
    chmod 600 "$APP_DIR/.env"
fi

sed "s|/usr/bin/python3|$APP_DIR/.venv/bin/python|" "$APP_DIR/openwrt/cubie-a5e-telegram-bot.init" > "$SERVICE"
chmod 755 "$SERVICE"
"$SERVICE" enable

echo "Installation files are ready. Configure $APP_DIR/.env, then run: $SERVICE start"
