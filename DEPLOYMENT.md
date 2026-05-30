# 🚀 Serverga deploy qilish — to'liq qo'llanma

Bu qo'llanma Ubuntu/Debian serverda Tanishuv Bot'ni 24/7 ishlatish uchun.

## 📋 Talablar

- Ubuntu 20.04+ yoki Debian 11+ VPS
- Root yoki sudo huquqi
- Telegram Bot Token va Admin ID

## ⚡ Tez deploy (avtomatik script — 5 daqiqa)

### 1. Serverga ulaning (SSH orqali)

```bash
ssh root@SIZNING_SERVER_IP
```

### 2. Loyihani yuklab oling

```bash
cd /tmp
git clone https://github.com/Sunnatullo-Dev/Robot.git tanishuv-bot
cd tanishuv-bot
```

### 3. Avtomatik o'rnatish

```bash
sudo bash deploy/install.sh
```

Skript quyidagilarni qiladi:
- ✅ Python va kerakli paketlarni o'rnatadi
- ✅ `botuser` foydalanuvchi yaratadi
- ✅ Loyihani `/opt/tanishuv-bot` ga ko'chiradi
- ✅ Virtual muhit yaratadi va kutubxonalarni o'rnatadi
- ✅ systemd service'ni ro'yxatga oladi
- ✅ Avtomatik ishga tushish va qayta ishga tushishni sozlaydi

### 4. `.env` faylini to'ldiring

```bash
sudo nano /opt/tanishuv-bot/.env
```

To'ldiriladigan maydonlar:

```ini
BOT_TOKEN=8402303733:AAEk0BU6HH7Oz7yYCm2mg_FFv-_0MdRy_LA
ADMIN_IDS=7566796449
DB_PATH=/opt/tanishuv-bot/tanishuv.db
PREMIUM_PRICE=9 999 so'm
PREMIUM_CARD=5614 6847 0909 0318
PREMIUM_DAYS=30
```

Ctrl+O → Enter → Ctrl+X bilan saqlang.

### 5. Botni ishga tushiring

```bash
sudo systemctl start tanishuv-bot
```

### 6. Tekshirish

```bash
# Holatni ko'rish
sudo systemctl status tanishuv-bot

# Loglarni real-time kuzatish
sudo journalctl -u tanishuv-bot -f
```

`Bot ishga tushdi` chiqsa — tayyor! Telegramda botni sinab ko'ring.

---

## 🔄 Yangilash (yangi kod tortish)

Loyiha GitHub'da yangilangach:

```bash
sudo bash /opt/tanishuv-bot/deploy/update.sh
```

Yoki qo'lda:

```bash
cd /opt/tanishuv-bot
sudo -u botuser git pull
sudo systemctl restart tanishuv-bot
```

---

## 🔧 Foydali buyruqlar

### Botni boshqarish

```bash
sudo systemctl start tanishuv-bot      # Ishga tushirish
sudo systemctl stop tanishuv-bot       # To'xtatish
sudo systemctl restart tanishuv-bot    # Qayta ishga tushirish
sudo systemctl status tanishuv-bot     # Holat
sudo systemctl enable tanishuv-bot     # Server qayta yoqilganda avto-start
sudo systemctl disable tanishuv-bot    # Avto-start'ni o'chirish
```

### Loglar

```bash
# Real-time kuzatish
sudo journalctl -u tanishuv-bot -f

# Oxirgi 100 qator
sudo journalctl -u tanishuv-bot -n 100

# Bugungi loglar
sudo journalctl -u tanishuv-bot --since today

# Faqat xatolar
sudo journalctl -u tanishuv-bot -p err

# Sana bo'yicha
sudo journalctl -u tanishuv-bot --since "2026-05-29" --until "2026-05-30"
```

### DB backup

```bash
# Qo'lda backup
sudo cp /opt/tanishuv-bot/tanishuv.db /opt/tanishuv-bot/backups/db-$(date +%F).db

# Avtomatik kunlik backup uchun cron qo'shing:
sudo crontab -e
# Ushbu qatorni qo'shing:
0 3 * * * cp /opt/tanishuv-bot/tanishuv.db /opt/tanishuv-bot/backups/db-$(date +\%F).db
```

Yoki bot ichidan: **/admin → 🧪 Dev Tools → 💾 DB Backup** — Telegram orqali yuboradi.

---

## 🛡 Xavfsizlik tavsiyalar

### 1. Firewall

```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 443/tcp  # HTTPS (Telegram polling uchun)
```

### 2. SSH kalit autentifikatsiyasi

Parol o'rniga SSH kalit ishlating:

```bash
# Lokal kompyuterda
ssh-copy-id root@SIZNING_SERVER_IP

# Keyin /etc/ssh/sshd_config da:
# PasswordAuthentication no
```

### 3. .env xavfsizligi

```bash
sudo chmod 600 /opt/tanishuv-bot/.env
sudo chown botuser:botuser /opt/tanishuv-bot/.env
```

### 4. Avtomatik yangilanish (xavfsizlik patchlari)

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 🐳 Docker bilan (alternativ)

Docker bilan ishlatish istasangiz, quyidagi `Dockerfile` yaratish mumkin:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

```bash
docker build -t tanishuv-bot .
docker run -d --name tanishuv-bot \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  tanishuv-bot
```

---

## 🆘 Muammolarni hal qilish

### Bot ishga tushmayapti

```bash
# Loglarda xato qidiring
sudo journalctl -u tanishuv-bot -n 50 --no-pager

# Konfiguratsiya tekshiruvi
sudo -u botuser /opt/tanishuv-bot/venv/bin/python /opt/tanishuv-bot/bot.py
```

### TelegramConflictError

Ikkita bot bir vaqtda ishlayotgan ko'rinadi:

```bash
# Mahalliy ishga tushgan botingizni o'chiring (PowerShell'da Ctrl+C)
# Yoki boshqa serverdagi botni to'xtating
sudo systemctl stop tanishuv-bot  # Vaqtinchalik
```

### DB locked

```bash
# Bot yoki boshqa jarayon DB'ni qulflagan
sudo systemctl restart tanishuv-bot
```

### Disk to'lganda

```bash
# Loglarni tozalash
sudo journalctl --vacuum-time=7d

# Eski backup'larni o'chirish
sudo find /opt/tanishuv-bot/backups -mtime +30 -delete
```

### Foydalanuvchi soni juda ko'p (10k+)

PostgreSQL'ga o'tish:

1. PostgreSQL o'rnatish: `sudo apt install postgresql`
2. DB yaratish va asyncpg kutubxonasini qo'shish
3. `database/db.py` ni asyncpg'ga moslashtirish
4. SQLite'dan ma'lumotlarni migratsiya qilish

---

## 🌐 Recommendation: Server tanlash

| Provider | Narxi | Joylashuvi | Tavsiya |
|----------|-------|------------|---------|
| **Hetzner** | ~$4/oy | EU | ✅ Eng arzon va sifatli |
| **DigitalOcean** | $4-6/oy | Global | ✅ Boshlovchi uchun ideal |
| **Vultr** | $3.50/oy | Global | ✅ Kichik proyektlar |
| **AWS Lightsail** | $3.50/oy | Global | ⚠️ Limit'lar bor |
| **UZINFOCOM** | Mahalliy | O'zbekiston | ⚠️ Telegram bilan latency |

Telegram bot uchun **EU yoki Singapur** joylashuvi yaxshi (Telegram serverlari shu yerda).

Minimal talablar:
- RAM: 512 MB (1 GB tavsiya)
- CPU: 1 core
- Disk: 10 GB
- Bandwidth: 1 TB/oy

---

## 📞 Yordam kerakmi?

GitHub Issues: https://github.com/Sunnatullo-Dev/Robot/issues
