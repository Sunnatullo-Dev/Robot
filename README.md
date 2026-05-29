# 💞 Tanishuv Bot

> Telegram platformasidagi zamonaviy anonim tanishuv (matchmaking) tizimi.
> Foydalanuvchilar o'ziga mos insonlarni topadi, xavfsiz suhbat quradi va yangi tanishuvlar orttiradi.

Bot avtomatik moslashtirish, lokatsiya asosidagi qidiruv, anonim chat va moderatsiya tizimlari bilan jihozlangan.

---

## 📋 Mundarija

- [👤 Foydalanuvchi funksiyalari](#-foydalanuvchi-funksiyalari)
- [🛠 Admin paneli](#-admin-paneli)
- [🛡 Xavfsizlik](#-xavfsizlik-arxitekturasi)
- [⚡ Ishga tushirish](#-ishga-tushirish)
- [🗂 Texnologiyalar](#-texnologiyalar)

---

## 👤 Foydalanuvchi funksiyalari

### 🚀 Asosiy buyruqlar

| Buyruq | Tavsifi |
|--------|---------|
| `/start` | Botni ishga tushirish va anketa yaratish |
| `/profile` | Profilni ko'rish va tahrirlash |
| `/search` | Anketalarni qidirish |
| `/matches` | Mosliklar ro'yxati |
| `/help` | Qo'llanma va yordam |
| `/cancel` | Joriy amalni bekor qilish (har qanday joydan) |

### 📝 Profil yaratish tizimi

Foydalanuvchi bir necha bosqich orqali anketa yaratadi:

**Kiritiladigan ma'lumotlar:**

- 👤 **Ism** — 2–30 belgi
- 🎂 **Yosh** — 14–99
- ⚧ **Jins** — Erkak / Ayol
- 🏙 **Viloyat tanlash** — O'zbekistonning 14 ta viloyati inline tugmalardan
- 🏘 **Tuman/shahar tanlash** — viloyatdagi ~10–20 ta tuman
- 📍 **GPS lokatsiya** (ixtiyoriy) — yaqindagi odamlarni topish uchun
- 💬 **Bio** — qisqacha ma'lumot (300 belgigacha)
- 📷 **Profil rasmi**

**Avtomatik matching:**
- Erkak foydalanuvchilarga ayollar ko'rsatiladi
- Ayol foydalanuvchilarga erkaklar ko'rsatiladi

### 🔍 Aqlli qidiruv tizimi

Bot foydalanuvchilarga mos anketalarni quyidagi parametrlar asosida ko'rsatadi:

- Yosh
- Jins
- Hudud
- Lokatsiya masofasi
- Faollik holati

**Inline boshqaruv:**

- ❤️ **Like** — yoqdi
- 👎 **Skip** — keyingisiga o'tish
- 🚫 **Report** — shikoyat qilish
- 🏠 **Menu** — asosiy menyuga qaytish

**Lokatsiya algoritmi:**

GPS yoqilgan foydalanuvchilar uchun eng yaqin odamlar birinchi chiqariladi (Haversine formulasi asosida).

> 📍 Sizdan 12 km uzoqlikda

### 💞 Match tizimi

Ikki foydalanuvchi bir-biriga ❤️ bosganda:

- 💞 Match yaratiladi
- Har ikki tomonga bildirishnoma yuboriladi
- Username almashish imkoniyati paydo bo'ladi
- Match tarixda saqlanadi

### 💬 Anonim chat

Moslik yaratilgandan keyin foydalanuvchilar anonim chat boshlashi mumkin.

**Qo'llab-quvvatlanadigan formatlar:**

- Matn
- Rasm
- Sticker
- Voice message
- Video message

**Xavfsizlik:**

- Telefon raqami yashirin
- Telegram ID ko'rinmaydi
- Istalgan vaqtda chatni tugatish mumkin
- Partner bloklansa, suhbat avtomatik to'xtaydi

### ⚙️ Profilni boshqarish

Foydalanuvchi quyidagilarni o'zgartira oladi:

- ✏️ Ism
- 🎂 Yosh
- 🏙 Hudud
- 📍 Lokatsiya
- 💬 Bio
- 📷 Rasm

**Profilni o'chirish:**

Profil qidiruvdan yashiriladi, lekin ma'lumotlar bazasida saqlanadi (qayta tiklash imkoni).

### 🚫 Moderatsiya tizimi

**Report sabablari:**

- Spam / reklama
- Soxta profil
- Haqorat
- 18+ kontent
- Boshqa

**Avtomatik himoya:**

- 3 ta report → auto-ban
- Adminlarga avtomatik xabar
- Spam throttling
- HTML sanitization
- Global error handling

---

## 🛠 Admin paneli

### Admin buyruqlari

| Buyruq | Tavsifi |
|--------|---------|
| `/admin` | Admin panel (inline menyu) |
| `/stats` | Tezkor statistika |
| `/seed` | Test foydalanuvchilarni yaratish |
| `/unseed` | Test foydalanuvchilarni o'chirish |
| `/cancel` | Joriy amalni bekor qilish |

### 📊 Statistika tizimi

Admin panel real-time statistikalarni ko'rsatadi:

- 👥 Jami foydalanuvchilar
- 🟢 Aktiv userlar
- 📝 Anketali userlar
- 🚫 Banlar
- ❤️ Like soni
- 💞 Matchlar
- ⚠️ Reportlar

### 📢 Broadcast tizimi

Admin barcha foydalanuvchilarga **istalgan turdagi xabarni** yubora oladi:

- 📝 Matn (HTML formatlash bilan)
- 📷 Rasm (caption bilan)
- 🎬 Video
- 🎵 Ovozli xabar
- 📁 Hujjat (file)
- 🎨 Stiker
- 🎞 Animatsiya / GIF
- ↪️ Forward qilingan xabar

**Qo'shimcha imkoniyatlar:**

- Real-time progress indikatori
- Telegram rate-limit himoyasi (~25 msg/sek)
- Yetkazib bera olmagan xabarlar uchun log
- Bloklangan foydalanuvchilar avtomatik o'tkazib yuboriladi

### 🧪 Test foydalanuvchilar tizimi

Developerlar uchun maxsus seed tizimi mavjud.

**Terminal orqali (tavsiya etiladi):**

```bash
python -m tools.seed           # 15 ta test anketa qo'shadi
python -m tools.seed --delete  # hammasini o'chiradi
```

**Bot orqali:**

- `/seed` — bitta rasm yuborib 15 ta anketa yaratish
- `/unseed` — barchasini o'chirish

Test anketa ID lari `9_000_000_001` dan `9_000_000_015` gacha — real Telegram foydalanuvchilariga to'qnashmaydi.

---

## 🛡 Xavfsizlik arxitekturasi

**Himoya mexanizmlari:**

- **Flood control** — har bir foydalanuvchi 0.5 sek/xabar, 0.3 sek/tugma cheklovi
- **Auto-ban system** — 3 ta shikoyat → avtomatik blok
- **BannedMiddleware** — bloklanganlar har qanday tugma/buyruqdan to'siladi
- **Exception logging** — har bir xato logga yoziladi
- **Conflict protection** — ikki bot bir vaqtda ishlasa, retry mexanizmi
- **Secure HTML escaping** — foydalanuvchi matni `<script>` kabi belgilar bilan ham xavfsiz
- **Global error handler** — kutilmagan xato botni to'xtatib qo'ymaydi

---

## ⚡ Ishga tushirish

### 1. Talablar

- Python 3.10+
- Telegram bot token ([@BotFather](https://t.me/BotFather) dan)
- Telegram user ID ([@userinfobot](https://t.me/userinfobot) dan)

### 2. Loyihani yuklash

```bash
git clone https://github.com/Sunnatullo-Dev/Robot.git
cd Robot
```

### 3. Virtual muhit va kutubxonalar

```bash
python -m venv venv
venv\Scripts\activate           # Windows
# yoki: source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 4. Konfiguratsiya

`.env.example` ni `.env` ga nusxa qiling va to'ldiring:

```ini
BOT_TOKEN=123456:ABC-DEF-sizning-tokeningiz
ADMIN_IDS=123456789
DB_PATH=tanishuv.db
```

> Bir nechta admin uchun ID larni vergul bilan ajrating: `ADMIN_IDS=111,222,333`

### 5. Ishga tushirish

```bash
python bot.py
```

Konsolda `Bot ishga tushdi` ko'rinsa — bot tayyor.

### 6. Test ma'lumotlar (ixtiyoriy)

```bash
python -m tools.seed
```

---

## 🗂 Texnologiyalar

**Backend:**

- Python 3.11
- aiogram 3.x (zamonaviy Telegram framework)
- asyncio arxitekturasi

**Ma'lumotlar bazasi:**

- SQLite (aiosqlite asinxron drayveri)
- Migration tizimi (eski DB avtomatik yangilanadi)
- Index'lar tezkor qidiruv uchun

**Arxitektura:**

```
Tanishuv_Bot/
├── bot.py                  # Main entry
├── config.py               # .env'dan sozlamalar
├── requirements.txt
│
├── handlers/               # Foydalanuvchi va admin handlerlari
│   ├── start.py
│   ├── registration.py
│   ├── profile.py
│   ├── search.py
│   ├── matches.py
│   ├── chat.py
│   └── admin.py
│
├── database/               # SQLite + queries
│   ├── db.py
│   └── models.py
│
├── middlewares/            # Throttling + Banned check
│   ├── throttling.py
│   └── banned.py
│
├── keyboards/              # Reply va inline tugmalar
│   ├── reply.py
│   └── inline.py
│
├── states/                 # FSM holatlar
│   └── user_states.py
│
├── data/                   # Statik ma'lumotlar
│   ├── regions.py          # Viloyatlar va tumanlar
│   └── test_users.py       # Test foydalanuvchilar
│
├── utils/                  # Yordamchi funksiyalar
│   └── helpers.py          # haversine, esc, format_profile
│
└── tools/                  # Terminal scriptlari
    └── seed.py             # Test anketalarni avto yaratish
```

---

## 🎯 Loyiha maqsadi

Telegram ekotizimi ichida:

- **xavfsiz**
- **tezkor**
- **anonim**
- **zamonaviy**

tanishuv platformasini yaratish.

Bot mobil ilovasiz ishlaydi va to'liq Telegram interfeysiga moslashgan.

---

## 📄 Litsenziya

Bepul foydalanish uchun. Modifikatsiya va tarqatish ruxsat etilgan.

---

🔗 **GitHub:** https://github.com/Sunnatullo-Dev/Robot
