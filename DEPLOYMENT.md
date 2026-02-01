# 🚀 Deployment Guide - AuctionBot

دليل شامل للـ deployment على Railway

**المطور:** دارك  
**النسخة:** 3.0.0

---

## ✅ Pre-Deployment Checklist

قبل ما تبدأ، تأكد من:

- [ ] عندك حساب Discord Developer
- [ ] عندك حساب Railway (مجاني)
- [ ] عندك حساب GitHub (اختياري لكن موصى به)
- [ ] قاعدة بيانات PostgreSQL جاهزة

---

## 🎯 Step-by-Step Deployment

### المرحلة 1: إعداد Discord Bot

```bash
1. اذهب إلى: https://discord.com/developers/applications

2. New Application
   - الاسم: AuctionBot (أو أي اسم تحبه)
   - Create

3. Bot Section:
   - Add Bot
   - Reset Token → انسخ Token ✅
   - ⚠️ احفظه في مكان آمن!

4. Privileged Gateway Intents:
   ☑️ PRESENCE INTENT
   ☑️ SERVER MEMBERS INTENT
   ☑️ MESSAGE CONTENT INTENT
   - Save Changes

5. OAuth2 → URL Generator:
   Scopes:
   ☑️ bot
   ☑️ applications.commands
   
   Bot Permissions:
   ☑️ Administrator
   (أو اختر صلاحيات محددة إذا تبي)

6. انسخ Generated URL
   - افتحه في متصفح
   - اختر سيرفرك
   - Authorize

7. الحصول على Server ID:
   - Discord Settings → Advanced → Developer Mode ✅
   - انقر يمين على اسم السيرفر
   - Copy Server ID ✅
```

---

### المرحلة 2: إعداد قاعدة البيانات

#### خيار 1: Railway PostgreSQL (سريع وسهل) ⭐

```bash
1. Railway Dashboard
2. New Project
3. Add Service → Database → PostgreSQL
4. انتظر 30 ثانية حتى يتم الإنشاء
5. PostgreSQL Service → Variables
6. انسخ DATABASE_URL ✅
```

#### خيار 2: Supabase (مجاني للأبد) 🎁

```bash
1. https://supabase.com → Sign Up
2. New Project:
   - Name: auctionbot
   - Database Password: اختر كلمة مرور قوية ✅
   - Region: اختر الأقرب لك
   - Create

3. انتظر حتى يتم الإنشاء (2-3 دقائق)

4. Settings → Database:
   - Connection String → Session mode
   - انسخ Connection String ✅
   - غيّر [YOUR-PASSWORD] بكلمة المرور اللي اخترتها

مثال:
postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres

يصير:
postgresql://postgres.xxxxx:MyStrongPass123@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

---

### المرحلة 3: رفع الكود على GitHub

#### الطريقة 1: عبر GitHub Desktop

```bash
1. حمل GitHub Desktop
2. File → New Repository:
   - Name: auctionbot
   - Path: مكان الملفات
   - Create Repository

3. Publish Repository:
   - اختر Private أو Public
   - Publish
```

#### الطريقة 2: عبر Git Command Line

```bash
# في مجلد المشروع:
git init
git add .
git commit -m "Initial commit - AuctionBot v3.0"
git branch -M main
git remote add origin https://github.com/your-username/auctionbot.git
git push -u origin main
```

#### الطريقة 3: رفع يدوي

```bash
1. GitHub → New Repository
2. ارفع الملفات واحد واحد أو عبر Drag & Drop
```

---

### المرحلة 4: Deploy على Railway

```bash
1. Railway Dashboard → New Project

2. Deploy from GitHub repo:
   - Connect GitHub (إذا أول مرة)
   - اختر Repository: auctionbot
   - Deploy

3. انتظر حتى يتم Build (2-3 دقائق)

4. Settings → Variables → Add Variables:

   ⚠️ مهم جداً: لا تضع مسافات أو علامات اقتباس!

   DISCORD_TOKEN
   MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.GAbCdE.abc123defg

   DATA
   postgresql://user:pass@host:5432/db

   ALLOWED_GUILD_ID (اختياري)
   1234567890

5. Save Variables → Redeploy
```

---

### المرحلة 5: التحقق من التشغيل

```bash
1. Railway → Deployments → Latest

2. View Logs

3. ابحث عن هذه الرسائل:

   ✅ علامات النجاح:
   ===============================================
   ✅ Database connected successfully!
   ✅ Commands synced!
   🎉 BOT IS READY AND OPERATIONAL!
   ✅✅✅ نجحنا! البوت شغال 100% ✅✅✅
   ===============================================

   ❌ علامات الفشل:
   ❌❌❌ فشلنا! Discord Token خاطئ ❌❌❌
   ❌❌❌ فشلنا! حدث خطأ ❌❌❌
```

---

## 🎮 أول اختبار

```bash
# في Discord، جرب:
/مزاد start:1m min_inc:100k duration:5

# إذا اشتغل الأمر:
✅✅✅ تمام! البوت شغال 100% ✅✅✅

# إذا الأمر ما ظهر:
⏳ انتظر 5-10 دقائق (Discord يأخذ وقت)
```

---

## 🐛 Troubleshooting

### المشكلة 1: البوت offline

```bash
🔍 Check:
1. Railway Logs → ابحث عن ❌
2. Discord Developer Portal → Bot → Token صحيح؟
3. Intents مفعلة؟
4. Railway → Variables → DISCORD_TOKEN صحيح؟

💡 Solution:
- أعد إنشاء Token في Discord
- احذف المسافات من Token في Railway
- Redeploy
```

### المشكلة 2: Database Error

```bash
🔍 Check:
1. Railway Logs → "Database connection failed"?
2. DATA في Variables صحيح؟
3. Connection String كامل؟

💡 Solution:
- في Supabase: استخدم Session mode (مو Direct)
- تأكد من كلمة المرور صحيحة
- تأكد من عدم وجود مسافات
```

### المشكلة 3: الأوامر لا تظهر

```bash
🔍 Check:
1. Logs → "Commands synced!" موجود؟
2. Intents مفعلة في Discord Portal؟
3. البوت لديه صلاحيات في السيرفر؟

💡 Solution:
- انتظر 10 دقائق
- اعمل kick للبوت ثم أضفه مرة ثانية
- تحقق من صلاحيات Administrator
```

### المشكلة 4: Build Failed

```bash
🔍 Check:
1. Logs → وش الخطأ؟
2. requirements.txt موجود؟
3. Procfile موجود؟
4. runtime.txt موجود؟

💡 Solution:
- تأكد من جميع الملفات موجودة
- GitHub → شوف الملفات ظاهرة؟
- Railway → Settings → Rebuild
```

---

## 📊 مراقبة البوت

### في Railway:

```bash
1. Metrics:
   - CPU Usage
   - Memory Usage
   - Network

2. Logs:
   - Real-time monitoring
   - Error tracking
   - Event logging

3. Variables:
   - Update anytime
   - Auto-redeploy
```

### في Discord:

```bash
1. Bot Status:
   - Online = ✅
   - Offline = ❌

2. Commands:
   - / → يجب أن تظهر الأوامر

3. Test:
   - /مزاد → يجب أن يعمل
```

---

## 🔐 الأمان

### ⚠️ لا تشارك أبداً:

```bash
❌ DISCORD_TOKEN
❌ DATABASE_URL
❌ .env file
❌ Railway Variables
```

### ✅ استخدم Guild Lock:

```bash
# في Railway Variables:
ALLOWED_GUILD_ID=1234567890

# البوت سيعمل فقط في هذا السيرفر
```

---

## 💾 Backup

### قاعدة البيانات:

```bash
# Railway PostgreSQL:
1. Data → Connect
2. Download Backup
3. احفظ الملف

# Supabase:
1. Database → Backups
2. Create Backup
3. Download
```

### الكود:

```bash
# GitHub:
1. Repository → Code → Download ZIP
2. أو استخدم git clone
```

---

## 🔄 التحديثات

### تحديث الكود:

```bash
1. عدّل الملفات محلياً
2. git add .
3. git commit -m "Updated ..."
4. git push
5. Railway سيعمل deploy تلقائياً!
```

### تحديث المكتبات:

```bash
1. عدّل requirements.txt
2. git push
3. Railway سيثبت التحديثات
```

---

## 📈 Performance Tips

### تحسين الأداء:

```bash
1. استخدم Railway PostgreSQL (أسرع من Supabase)
2. راقب Memory Usage في Metrics
3. نظف قاعدة البيانات بانتظام
4. استخدم Guild Lock لتقليل الحمل
```

---

## 🎓 الموارد المفيدة

- [Railway Docs](https://docs.railway.app)
- [Discord.py Docs](https://discordpy.readthedocs.io)
- [Supabase Docs](https://supabase.com/docs)
- [PostgreSQL Docs](https://www.postgresql.org/docs)

---

## ✅ Final Checklist

قبل ما تعتبر البوت جاهز:

- [ ] البوت online في Discord
- [ ] جميع الأوامر تشتغل
- [ ] قاعدة البيانات متصلة
- [ ] Logs ما فيها أخطاء
- [ ] تم اختبار `/مزاد`
- [ ] Guild Lock مفعل (اختياري)
- [ ] Backup تم حفظه

**إذا كل شي ✅ → مبروك! البوت جاهز 🎉**

---

## 🆘 المساعدة

إذا واجهت أي مشكلة:

1. ✅ شوف Logs في Railway
2. ✅ راجع هذا الدليل
3. ✅ تحقق من Variables
4. ✅ جرب Redeploy

**🔥 بالتوفيق يا دارك! 🔥**

---

**آخر تحديث:** 2024
**النسخة:** 3.0.0 Railway Edition
**المطور:** دارك - السماء الجنوبية
