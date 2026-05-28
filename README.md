# 💞 Tanishuv Bot

Telegram tanishuv (dating) boti — **aiogram 3.x** + **SQLite** asosida yozilgan, to'liq ishlaydigan, zamonaviy ko'rinishdagi bot. @luramatchbot ga muqobil sifatida tayyorlangan, lekin ko'plab qo'shimcha imkoniyatlar bilan.

## ✨ Imkoniyatlar

- 📝 **Anketa yaratish** — ism, yosh, jins, kimni qidirayotgani, shahar, bio, rasm
- 🔍 **Aqlli qidiruv** — jins va qidiruv yo'nalishi bo'yicha filtrlash
- ❤️ **Like / Dislike** tizimi (Tinder uslubida)
- 💞 **Match** — ikki tomon ham like bossa, bir-biriga xabar yetadi va username almashinadi
- 💬 **Anonim suhbat** — bot orqali xabarlarni uzatish (matn, rasm, ovoz, stiker)
- 🚫 **Shikoyat tizimi** — 3 ta shikoyatda avto-ban
- 🛠 **Admin panel** — statistika, broadcast, ban/unban
- 🛡 **Throttling** — spam'ga qarshi
- ✏️ **Profilni tahrirlash** — istalgan vaqtda ism/yosh/rasm o'zgartirish

## 📦 O'rnatish

### 1. Python 3.10+ o'rnating
Python rasmiy saytidan yoki Microsoft Store dan.

### 2. Loyihani yuklab oling va papkaga kiring
```powershell
cd C:\Users\Ucer\Desktop\Tanishuv_Bot
```

### 3. Virtual muhit yarating va kutubxonalarni o'rnating
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Bot token oling
1. Telegramda [@BotFather](https://t.me/BotFather) ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomi va username bering
4. Tokenni nusxalang

### 5. `.env` faylini yarating
`.env.example` ni `.env` ga nusxa qiling va to'ldiring:

```ini
BOT_TOKEN=123456:ABC-DEF-sizning-tokeningiz
ADMIN_IDS=123456789
DB_PATH=tanishuv.db
```

> **ADMIN_IDS** — bu sizning Telegram ID'ingiz. [@userinfobot](https://t.me/userinfobot) orqali bilib olishingiz mumkin. Bir nechta admin bo'lsa, vergul bilan ajrating: `111,222,333`.

### 6. Botni ishga tushiring
```powershell
python bot.py
```

Konsolda `Bot ishga tushdi` yozuvi paydo bo'lsa — bot tayyor.

## 📁 Loyiha tuzilishi

```
Tanishuv_Bot/
├── bot.py                  # Asosiy entry point
├── config.py               # Sozlamalar
├── requirements.txt
├── .env                    # Token va sozlamalar (siz yaratasiz)
├── .env.example
│
├── database/
│   ├── db.py               # Jadval yaratish
│   └── models.py           # CRUD funksiyalar
│
├── handlers/
│   ├── start.py            # /start, /help
│   ├── registration.py     # Anketa yaratish
│   ├── profile.py          # Profil ko'rish/tahrirlash
│   ├── search.py           # Anketalarni ko'rish
│   ├── matches.py          # Mosliklar ro'yxati
│   ├── chat.py             # Anonim suhbat (relay)
│   └── admin.py            # Admin panel
│
├── keyboards/
│   ├── reply.py            # Reply tugmalar
│   └── inline.py           # Inline tugmalar
│
├── states/
│   └── user_states.py      # FSM holatlar
│
├── middlewares/
│   └── throttling.py       # Anti-spam
│
└── utils/
    └── helpers.py          # Yordamchi funksiyalar
```

## 🎮 Botdan foydalanish

**Foydalanuvchi uchun:**
- `/start` — botni ishga tushirish va anketa yaratish
- `/profile` — o'z anketangizni ko'rish
- `/search` — yangi anketalarni ko'rish
- `/matches` — mosliklar ro'yxati
- `/help` — yordam

**Admin uchun:**
- `/admin` — admin panel ochish
- `/stats` — qisqacha statistika

## 🚀 Server'da ishga tushirish (production)

### systemd service (Linux)
`/etc/systemd/system/tanishuv-bot.service`:
```ini
[Unit]
Description=Tanishuv Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/Tanishuv_Bot
ExecStart=/home/botuser/Tanishuv_Bot/.venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable tanishuv-bot
sudo systemctl start tanishuv-bot
sudo journalctl -u tanishuv-bot -f
```

### Windows Task Scheduler
"Task Scheduler → Create Basic Task → Daily/On startup" — `python.exe` ni `bot.py` ga yo'naltiring.

## 🛠 Texnologiyalar

- **aiogram 3.13** — Telegram Bot API uchun zamonaviy Python framework
- **aiosqlite** — Asinxron SQLite drayveri
- **python-dotenv** — Environment variable boshqaruvi

## 📝 Litsenziya

Bepul foydalanish uchun. Sotmang, lekin yaxshilang!

---

**@luramatchbot dan ustunliklar:**
- ✅ Tezroq (asinxron arxitektura)
- ✅ Anonim suhbat to'liq qo'llab-quvvatlanadi (matn, rasm, ovoz, stiker)
- ✅ Avtomatik anti-spam (throttling middleware)
- ✅ Avto-moderatsiya (3 shikoyatda ban)
- ✅ Admin broadcast — barcha foydalanuvchilarga xabar
- ✅ To'liq ochiq kod — istalgan funksiyani qo'shish/o'zgartirish mumkin
