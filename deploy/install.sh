#!/usr/bin/env bash
# Tanishuv Bot — Ubuntu/Debian uchun avtomatik o'rnatish skripti.
#
# Foydalanish:
#   sudo bash deploy/install.sh
#
# Skript:
# 1. Foydalanuvchi yaratadi (botuser)
# 2. /opt/tanishuv-bot ga loyihani ko'chiradi
# 3. Python venv yaratadi va kutubxonalarni o'rnatadi
# 4. systemd service'ni o'rnatadi
# 5. .env ni yaratish bo'yicha yo'riqnoma beradi
set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
    echo "❌ Bu skript root sifatida ishga tushishi kerak: sudo bash deploy/install.sh"
    exit 1
fi

BOT_DIR="/opt/tanishuv-bot"
BOT_USER="botuser"
SERVICE_NAME="tanishuv-bot"

echo "🚀 Tanishuv Bot — Server o'rnatish skripti"
echo "=========================================="
echo ""

# 1. Tizimni yangilash
echo "📦 1/7  Tizim yangilanmoqda..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git rsync

# 2. Foydalanuvchi yaratish
echo "👤 2/7  Foydalanuvchi yaratilmoqda..."
if ! id -u "$BOT_USER" >/dev/null 2>&1; then
    useradd -r -s /bin/false -d "$BOT_DIR" "$BOT_USER"
    echo "   ✓ Foydalanuvchi yaratildi: $BOT_USER"
else
    echo "   ✓ Mavjud: $BOT_USER"
fi

# 3. Loyihani ko'chirish
echo "📁 3/7  Loyiha fayllari ko'chirilmoqda..."
mkdir -p "$BOT_DIR"
# Joriy papkadan (deploy.sh ishga tushgan papkadan) bot fayllarini ko'chiramiz
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rsync -a --exclude='venv' --exclude='__pycache__' --exclude='.git' \
      --exclude='*.pyc' --exclude='.env' --exclude='*.db*' \
      "$SRC_DIR/" "$BOT_DIR/"

# 4. Virtual muhit
echo "🐍 4/7  Python virtual muhit yaratilmoqda..."
if [[ ! -d "$BOT_DIR/venv" ]]; then
    python3 -m venv "$BOT_DIR/venv"
fi
"$BOT_DIR/venv/bin/pip" install --upgrade pip --quiet
"$BOT_DIR/venv/bin/pip" install -r "$BOT_DIR/requirements.txt" --quiet
echo "   ✓ Kutubxonalar o'rnatildi"

# 5. .env tekshirish
echo "🔐 5/7  Konfiguratsiya tekshirilmoqda..."
if [[ ! -f "$BOT_DIR/.env" ]]; then
    cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
    chmod 600 "$BOT_DIR/.env"
    echo "   ⚠️  .env nusxasi yaratildi. Uni tahrirlash kerak!"
    NEEDS_ENV=1
else
    echo "   ✓ .env mavjud"
    NEEDS_ENV=0
fi

# 6. systemd service
echo "⚙️  6/7  Systemd xizmat sozlanmoqda..."
cp "$BOT_DIR/deploy/$SERVICE_NAME.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME" >/dev/null 2>&1
echo "   ✓ Xizmat ro'yxatga olindi"

# 7. Egalik
echo "🔧 7/7  Ruxsatlar o'rnatilmoqda..."
chown -R "$BOT_USER:$BOT_USER" "$BOT_DIR"

echo ""
echo "✅ O'rnatish yakunlandi!"
echo "=========================================="
echo ""

if [[ "$NEEDS_ENV" -eq 1 ]]; then
    echo "📝 BIRINCHI: .env faylini tahrirlang"
    echo "   sudo nano $BOT_DIR/.env"
    echo ""
    echo "   Eng kamida quyidagilarni to'ldiring:"
    echo "   - BOT_TOKEN"
    echo "   - ADMIN_IDS"
    echo "   - DB_PATH=/opt/tanishuv-bot/tanishuv.db"
    echo ""
fi

echo "🚀 IKKINCHI: Botni ishga tushiring"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
echo "📊 Holatni tekshirish:"
echo "   sudo systemctl status $SERVICE_NAME"
echo ""
echo "📜 Loglarni ko'rish:"
echo "   sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "🔄 Kodni yangilash (yangi o'zgartirishlar bo'lganda):"
echo "   cd $BOT_DIR && sudo -u $BOT_USER git pull"
echo "   sudo systemctl restart $SERVICE_NAME"
