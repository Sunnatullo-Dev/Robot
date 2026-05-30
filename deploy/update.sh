#!/usr/bin/env bash
# Tanishuv Bot — yangilash skripti.
# GitHub'dan eng so'nggi kodni tortib, kutubxonalarni yangilab,
# botni qayta ishga tushiradi.
#
# Foydalanish:
#   sudo bash /opt/tanishuv-bot/deploy/update.sh
set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
    echo "❌ sudo bilan ishga tushiring: sudo bash deploy/update.sh"
    exit 1
fi

BOT_DIR="/opt/tanishuv-bot"
BOT_USER="botuser"
SERVICE_NAME="tanishuv-bot"

echo "🔄 Tanishuv Bot — yangilanmoqda..."

# Git pull
echo "📥 1/3  GitHub'dan yangilash..."
cd "$BOT_DIR"
sudo -u "$BOT_USER" git fetch origin
sudo -u "$BOT_USER" git reset --hard origin/main

# Kutubxonalar
echo "📦 2/3  Kutubxonalar tekshirilmoqda..."
"$BOT_DIR/venv/bin/pip" install -r "$BOT_DIR/requirements.txt" --upgrade --quiet

# Restart
echo "🚀 3/3  Bot qayta ishga tushirilmoqda..."
systemctl restart "$SERVICE_NAME"
sleep 2
systemctl status "$SERVICE_NAME" --no-pager -l | head -15

echo ""
echo "✅ Yangilash yakunlandi!"
echo ""
echo "Loglar uchun: sudo journalctl -u $SERVICE_NAME -f"
