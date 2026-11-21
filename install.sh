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

if [ "$PM" = apk ]; then
    apk update
    apk add python3 py3-pip py3-virtualenv git ca-bundle
else
    opkg update
    opkg install python3 python3-pip git ca-bundle
fi

if [ ! -d "$APP_DIR/.git" ]; then
    git clone "$REPO_URL" "$APP_DIR"
else
    git -C "$APP_DIR" pull --ff-only
fi

if [ ! -x /usr/bin/python3 ]; then
    echo "Python 3 was not installed at /usr/bin/python3." >&2
    exit 1
fi

mkdir -p /etc/cubie-a5e-telegram-bot
cd "$APP_DIR"
python3 -m venv --system-site-packages .venv || {
    echo "Could not create virtualenv; install python3-venv/py3-virtualenv for this firmware." >&2
    exit 1
}
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo "Created $APP_DIR/.env. Edit TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID before starting."
fi

sed "s|/usr/bin/python3|$APP_DIR/.venv/bin/python|" "$APP_DIR/openwrt/cubie-a5e-telegram-bot.init" > "$SERVICE"
chmod 755 "$SERVICE"
"$SERVICE" enable
echo "Installation files are ready. Edit $APP_DIR/.env, then run: $SERVICE start"
