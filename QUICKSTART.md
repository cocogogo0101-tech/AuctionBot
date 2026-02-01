# ⚡ دليل البدء السريع - حل مشكلة Cloudflare

## 🎯 الهدف
تشغيل البوت على Render بدون مشاكل Rate Limiting

---

## 🚨 حل مشكلة Cloudflare 1015

### الطريقة 1: تغيير Region (الأسرع) ⭐

1. **اذهب إلى Render Dashboard**
2. **اختر Web Service الخاص بالبوت**
3. **Settings → Region**
4. **غيّر Region إلى:**
   - Europe (Frankfurt) - موصى به
   - Singapore
   - Ohio
5. **Deploy مرة أخرى**

---

### الطريقة 2: استخدام خدمة أخرى

إذا Render ما زال يعطي مشاكل:

#### أ) Railway.app (مجاني)
```bash
# 1. سجل في railway.app
# 2. New Project → Deploy from GitHub
# 3. اختر الريبو
# 4. أضف Environment Variables:
DISCORD_TOKEN=...
DATA=...
ALLOWED_GUILD_ID=...
```

#### ب) Replit (سهل جداً)
```bash
# 1. سجل في replit.com
# 2. Create Repl → Import from GitHub
# 3. في Secrets أضف المتغيرات
# 4. Run
```

#### ج) VPS (الأفضل للإنتاج)

**Hetzner** (€4/شهر - موصى به):
```bash
# 1. سجل في hetzner.com
# 2. اشترِ Cloud Server (CX11)
# 3. SSH إلى السيرفر:
ssh root@your-server-ip

# 4. ثبت المتطلبات:
apt update && apt upgrade -y
apt install python3 python3-pip git -y

# 5. استنسخ المشروع:
git clone your-repo-url
cd your-repo

# 6. ثبت المكتبات:
pip3 install -r requirements.txt

# 7. أنشئ .env:
nano .env
# أضف المتغيرات ثم احفظ (Ctrl+X, Y, Enter)

# 8. شغّل البوت:
python3 bot.py

# 9. للتشغيل الدائم (استخدم screen):
apt install screen -y
screen -S bot
python3 bot.py
# اضغط Ctrl+A ثم D للخروج
```

---

### الطريقة 3: تشغيل محلي (للاختبار)

```bash
# على جهازك:
git clone your-repo-url
cd your-repo
pip install -r requirements.txt

# أنشئ .env:
DISCORD_TOKEN=your_token
DATA=your_database_url
ALLOWED_GUILD_ID=your_guild_id

# شغّل:
python bot.py
```

---

## ✅ التحقق من نجاح التشغيل

عند التشغيل الناجح، ستشوف:

```
🤖 AuctionBot - السماء الجنوبية
🛡️ Self-Healing System Active
==================================================
🔌 Connecting to database...
✅ Database connected and tables ensured
==================================================
✅ Bot is ready and operational!
👤 Logged in as: BotName#1234 (ID: ...)
🗄️  Database: Connected
🌐 Guilds: 1
🔒 Guild Lock: ACTIVE (ID: ...)
📊 Total Errors: 0
==================================================
```

---

## 🔥 إذا ظهر Rate Limit:

```
⚠️ Rate limited by Discord! Status: 429
⏳ Waiting X seconds before retry...
```

**لا تقلق!** البوت سيعيد المحاولة تلقائياً.

**لكن إذا استمر:**
1. غيّر Region في Render
2. أو انتقل لخدمة أخرى (VPS موصى به)

---

## 📋 Checklist قبل التشغيل

- [ ] ✅ DISCORD_TOKEN صحيح (بدون مسافات)
- [ ] ✅ DATA connection string صحيح
- [ ] ✅ ALLOWED_GUILD_ID محدد (أو فارغ)
- [ ] ✅ Intents مفعلة في Discord Portal
- [ ] ✅ Bot في السيرفر المحدد
- [ ] ✅ Bot لديه صلاحيات كافية

---

## 🎮 أول أمر بعد التشغيل

```
/set_auction_channel #قناة-المزادات
/set_log_channel #قناة-اللوق
/set_auction_role @رواد-المزاد
```

ثم:
```
/لوحة_مزاد start:1m min_inc:100k duration:5
```

---

## 🆘 مشاكل شائعة

| المشكلة | الحل |
|---------|------|
| `Rate limited` | غيّر Region أو VPS |
| `Invalid token` | تحقق من DISCORD_TOKEN |
| `Database error` | تحقق من DATA string |
| `Commands not showing` | انتظر ساعة أو sync يدوي |
| `Bot offline` | شوف logs في Render |

---

## 📞 الدعم

**إذا واجهت مشاكل:**
1. اقرأ `TROUBLESHOOTING.md`
2. شوف logs في Render
3. تحقق من Environment Variables

**الملفات المساعدة:**
- `README.md` - التوثيق الكامل
- `TROUBLESHOOTING.md` - حل المشاكل التفصيلي
- `CHANGELOG.md` - التحديثات

---

**🚀 بالتوفيق يا دارك!**
