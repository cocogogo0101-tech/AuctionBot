# 🚀 دليل Railway - خطوة بخطوة

## 📋 ما تحتاجه

1. ✅ حساب Railway (مجاني): https://railway.app
2. ✅ حساب GitHub
3. ✅ Discord Bot Token
4. ✅ قاعدة بيانات PostgreSQL

---

## 🎯 الخطوات

### 1️⃣ إعداد Discord Bot

```bash
1. اذهب إلى: https://discord.com/developers/applications
2. New Application → اسم البوت
3. Bot → Reset Token → انسخ Token (احفظه!)
4. Bot → Privileged Gateway Intents:
   ☑️ PRESENCE INTENT
   ☑️ SERVER MEMBERS INTENT
   ☑️ MESSAGE CONTENT INTENT
5. OAuth2 → URL Generator:
   Scopes: ☑️ bot ☑️ applications.commands
   Permissions: ☑️ Administrator
6. انسخ الرابط وأضف البوت لسيرفرك
```

### 2️⃣ رفع الكود على GitHub

```bash
# إذا عندك git:
git init
git add .
git commit -m "Initial commit"
git remote add origin your-repo-url
git push -u origin main

# أو ببساطة:
# ارفع الملفات يدوياً على GitHub
```

### 3️⃣ إنشاء قاعدة بيانات

**الطريقة 1: Railway PostgreSQL (سهلة وسريعة)**
```bash
1. New Project
2. Add Service → Database → PostgreSQL
3. انتظر حتى يتم الإنشاء
4. Variables → DATABASE_URL (انسخه)
```

**الطريقة 2: Supabase (مجانية للأبد)**
```bash
1. https://supabase.com → New Project
2. Settings → Database
3. Connection String → Session mode
4. انسخ Connection String
5. غيّر [YOUR-PASSWORD] بكلمة المرور الفعلية
```

### 4️⃣ Deploy على Railway

```bash
1. New Project (إذا ما عندك)
2. Deploy from GitHub repo
3. اختر الريبو
4. Add Variables:
```

**المتغيرات المطلوبة:**
```env
DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.GAbCdE.abc123
DATA=postgresql://user:password@host:port/database
```

**المتغيرات الاختيارية:**
```env
ALLOWED_GUILD_ID=1234567890
```

**⚠️ مهم جداً:**
- لا تضع مسافات قبل أو بعد القيم
- لا تستخدم علامات اقتباس `"` أو `'`
- تأكد من نسخ Token كامل بدون قص

### 5️⃣ التحقق من التشغيل

```bash
1. Deployments → Latest
2. View Logs
3. ابحث عن:
   ✅✅✅ نجحنا! البوت شغال 100% ✅✅✅
```

**إذا شفت هذي الرسالة → تمام 100%! 🎉**

---

## 🔥 الحصول على Guild ID

```bash
1. Discord → User Settings → Advanced
2. فعّل Developer Mode
3. انقر يمين على اسم السيرفر
4. Copy Server ID
```

---

## 📊 مراقبة البوت

### في Railway Dashboard:
```bash
1. Metrics → شوف CPU, Memory, Network
2. Logs → شوف الأحداث المباشرة
3. Variables → تعديل المتغيرات
```

### الأحداث المهمة في Logs:
```
🚀 STARTING AUCTIONBOT...           # البوت يبدأ
✅ Database connected successfully!  # قاعدة البيانات متصلة
✅ Commands synced!                  # الأوامر متزامنة
🎉 BOT IS READY AND OPERATIONAL!    # جاهز تماماً
✅✅✅ نجحنا! البوت شغال 100% ✅✅✅  # نجاح كامل
```

### الأخطاء المحتملة:
```
❌❌❌ فشلنا! Discord Token خاطئ    # تحقق من Token
❌❌❌ فشلنا! حدث خطأ                # شوف التفاصيل
```

---

## 🛠️ حل المشاكل

### المشكلة: Railway يقول "Build Failed"

**الحل:**
```bash
1. تحقق من requirements.txt موجود
2. تحقق من Procfile موجود
3. تحقق من runtime.txt موجود
4. Rebuild من Dashboard
```

### المشكلة: البوت offline في Discord

**الحل:**
```bash
1. شوف Logs في Railway
2. ابحث عن "❌" في Logs
3. تحقق من:
   - DISCORD_TOKEN صحيح
   - Intents مفعلة في Discord Portal
   - البوت مو محظور من السيرفر
```

### المشكلة: الأوامر لا تظهر

**الحل:**
```bash
1. انتظر 5-10 دقائق (Discord يأخذ وقت)
2. تحقق من Intents مفعلة
3. تحقق من صلاحيات البوت
4. جرب kick & re-invite البوت
```

### المشكلة: Database Error

**الحل:**
```bash
1. تحقق من DATA في Variables
2. تأكد من Connection String كامل
3. في Supabase: استخدم Session mode (مو Direct)
4. تأكد من كلمة المرور صحيحة
```

---

## 💡 نصائح

### 1. استخدم Environment Groups
```bash
Railway → Settings → Environment Groups
أنشئ group للـ production
```

### 2. فعّل Notifications
```bash
Settings → Notifications
احصل على تنبيهات عند الأخطاء
```

### 3. راقب الـ Usage
```bash
Dashboard → Usage
تابع استهلاك الموارد
```

### 4. Backup قاعدة البيانات
```bash
# في Railway PostgreSQL:
Data → Connect → Download backup
```

---

## 📱 أول أوامر بعد التشغيل

```bash
# في Discord:
/مزاد start:1m min_inc:100k duration:5

# إذا اشتغل → البوت 100% تمام! 🎉
```

---

## 🎓 الموارد

- Railway Docs: https://docs.railway.app
- Discord.py Docs: https://discordpy.readthedocs.io
- Supabase Docs: https://supabase.com/docs

---

## ✅ Checklist قبل Deploy

- [ ] DISCORD_TOKEN موجود وصحيح
- [ ] DATA موجود وصحيح
- [ ] Intents مفعلة في Discord Portal
- [ ] البوت مضاف للسيرفر
- [ ] requirements.txt موجود
- [ ] Procfile موجود
- [ ] runtime.txt موجود

**إذا كل شي ✅ → Deploy الآن! 🚀**

---

**🔥 بالتوفيق يا دارك! 🔥**

أي مشكلة، شوف Logs في Railway وراسلني!
