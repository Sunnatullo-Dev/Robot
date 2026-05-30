# 🚀 Render.com'ga deploy qilish — to'liq qo'llanma

Render.com — Telegram bot uchun eng oson cloud platforma. GitHub'dan to'g'ridan-to'g'ri deploy, avtomatik HTTPS, monitoring va loglar.

## 📋 Reja

Telegram bot 24/7 ishlashi kerak. Render.com'da 2 ta variant:

| Plan | Narxi | Tavsifi |
|------|-------|---------|
| **Background Worker (Starter)** | $7/oy | ✅ 24/7 ishlaydi, sleep yo'q — **TAVSIYA** |
| Web Service (Free) | Bepul | ⚠️ 15 daq faolsiz qolsa, uxlab qoladi |

> 💡 **Bepul variant ham bor**, lekin uyquga ketadi. Telegram polling uxlab qolgan paytda xabarlarni o'tkazib yuboradi. Yaxshisi $7/oy to'lash yoki UptimeRobot bilan keepalive qilish.

## ⚡ Tez deploy — Background Worker (5 daqiqa)

### 1. Render.com'da ro'yxatdan o'ting

https://render.com → Sign up with GitHub

### 2. GitHub repo'ni ulang

Dashboard'da: **New +** → **Background Worker**

Yoki: **New +** → **Blueprint** (loyihangizdagi `render.yaml`'dan avto-sozlash)

### 3. Repo tanlang

**Sunnatullo-Dev/Robot** ni tanlang.

### 4. Sozlamalar (Blueprint avto-to'ldiradi):

| Maydon | Qiymat |
|--------|--------|
| Name | tanishuv-bot |
| Region | **Frankfurt** (EU — Telegram bilan tez) |
| Branch | main |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python bot.py` |
| Plan | **Starter** ($7/oy) |

### 5. Environment Variables ni kiriting

Render Dashboard → **Environment** bo'limi:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | `8402303733:AAEk...` (Telegram tokeningiz) |
| `ADMIN_IDS` | `7566796449` |
| `DB_PATH` | `/opt/render/project/src/data/tanishuv.db` |
| `CHANNEL_USERNAME` | `@your_channel` |
| `REQUIRE_SUBSCRIPTION` | `false` |
| `PYTHON_VERSION` | `3.11.0` |

> Premium narx va karta endi DB'da saqlanadi — admin paneldan `/admin → 💎 Premium narx` orqali tahrirlanadi.

### 6. Persistent Disk qo'shing (SQLite DB uchun)

**Settings → Disks → New Disk**:

| Maydon | Qiymat |
|--------|--------|
| Name | bot-data |
| Mount Path | `/opt/render/project/src/data` |
| Size | 1 GB |

Bu disk qayta deploy bo'lganda ham DB'ni saqlaydi.

### 7. Deploy bossangiz!

**Create Background Worker** → Render avtomatik:
- GitHub'dan kod oladi
- Python paketlarni o'rnatadi
- Botni ishga tushiradi

Bir necha daqiqada loglarda `Bot ishga tushdi` chiqadi.

---

## 🔄 Yangilanish (har gal kod o'zgartirsangiz)

Render `autoDeploy: true` bilan sozlangan:

```
git push origin main → Render avtomatik deploy
```

Yoki Dashboard'dan **Manual Deploy** tugmasini bosing.

---

## 📊 Loglarni kuzatish

Render Dashboard → **Logs** tabi:
- Real-time loglar
- Filtrlash (ERROR, WARN, INFO)
- Loglarni izlash

---

## 🆓 Bepul variant — Web Service + UptimeRobot

Agar $7/oy to'lashni xohlamasangiz, bepul Web Service'da quyidagicha qilish mumkin:

### 1. bot.py'ni o'zgartirish kerak

Render Web Service HTTP port'ini tinglashi shart. Bunga moslash uchun:

```python
# bot.py'ga qo'shing (asosiy kodning oxiriga):
from aiohttp import web
import os

async def health_check(request):
    return web.Response(text="OK")

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "10000")))
    await site.start()

# main() ichida polling'dan oldin:
await start_health_server()
```

### 2. Web Service yarating

**New +** → **Web Service** → GitHub repo

| Maydon | Qiymat |
|--------|--------|
| Build Command | `pip install -r requirements.txt aiohttp` |
| Start Command | `python bot.py` |
| Plan | **Free** |

### 3. UptimeRobot bilan keepalive

https://uptimerobot.com → bepul ro'yxat → New Monitor:

| Maydon | Qiymat |
|--------|--------|
| Monitor Type | HTTP(s) |
| URL | https://tanishuv-bot.onrender.com (Render URL) |
| Monitoring Interval | 5 minutes |

UptimeRobot har 5 daqiqada ping yuboradi → Render uyquga ketmaydi.

---

## 🛡 Xavfsizlik

- ✅ `BOT_TOKEN` — faqat Render Environment Variables'da, hech qachon kodda emas
- ✅ HTTPS — Render avtomatik
- ✅ `DB_PATH` — persistent disk'da (qayta deploy'da yo'qolmaydi)

---

## 🆘 Muammolarni hal qilish

### "Build failed"

Render Dashboard → **Events** ko'ring. Odatda:
- `requirements.txt` da xatolik → tuzating
- Python versiya noto'g'ri → `PYTHON_VERSION=3.11.0` ekanini tekshiring

### Bot javob bermayapti

1. Dashboard → **Logs** → ERROR'larni qidiring
2. `BOT_TOKEN` to'g'ri kiritilganmi?
3. `TelegramConflictError` — boshqa joyda ham bot ishlayapti, to'xtating

### DB yo'qolib qoldi

Persistent Disk qo'shilmagan. **Settings → Disks** dan qo'shing va `DB_PATH` ni `/opt/render/project/src/data/tanishuv.db` ga sozlang.

### Render Free Plan'da bot uxlab qoladi

Bu Free plan'ning cheklovi. Yechimlar:
1. Starter plan'ga o'tish ($7/oy)
2. UptimeRobot bilan keepalive (lekin Free Web Service uchun)

---

## 💰 Narxlar — taqqoslash

| Provider | Plan | Narxi | Tavsiya |
|----------|------|-------|---------|
| **Render Background Worker** | Starter | $7/oy | ✅ Eng oson |
| **Render Web Service + UptimeRobot** | Free | $0 | ⚠️ Murakkab sozlash |
| **Hetzner CX11 VPS** | — | €4/oy | ✅ Eng arzon, lekin Linux bilim kerak |
| **DigitalOcean Droplet** | Basic | $4/oy | ✅ Yaxshi |
| **Railway.app** | Hobby | $5/oy | ✅ Render'ga o'xshash |

---

## 📞 Yordam

Render Dashboard'da loglarni ko'rib chiqing va xatolik yuborsangiz, sizga yordam beraman.

🔗 https://render.com/docs
