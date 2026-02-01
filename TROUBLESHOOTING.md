# 🛠️ دليل حل المشاكل - AuctionBot

## 🔥 المشاكل الشائعة والحلول

### 1️⃣ خطأ Cloudflare 1015 (Rate Limiting)

**الأعراض:**
```
Error 1015: You are being rate limited
```

**الأسباب:**
- Discord/Cloudflare يحظر IP الخاص بـ Render
- كثرة محاولات الاتصال
- IP مشترك مع بوتات أخرى

**✅ الحلول:**

#### الحل 1: استخدام Proxy (موصى به لـ Render)
```bash
# في Render Environment Variables أضف:
HTTP_PROXY=http://your-proxy:port
HTTPS_PROXY=http://your-proxy:port
```

#### الحل 2: تغيير Region في Render
1. اذهب إلى Settings في Render
2. غيّر Region إلى منطقة أخرى (مثل Frankfurt بدلاً من Oregon)
3. أعد Deploy

#### الحل 3: استخدام VPS بدلاً من Render
- استخدم خدمات مثل:
  - DigitalOcean
  - Linode
  - Vultr
  - Hetzner (أرخص وأفضل)

#### الحل 4: Cloudflare Bypass Headers
البوت الآن يضيف headers تلقائياً، لكن يمكنك تحسينها:
```python
# في bot.py، أضف بعد import discord:
import aiohttp

# ثم عدّل connector:
connector = aiohttp.TCPConnector(
    limit=100,
    ttl_dns_cache=300,
    force_close=False
)
```

---

### 2️⃣ ValueError: Newline or carriage return detected

**الأعراض:**
```
ValueError: Newline or carriage return detected in headers
```

**السبب:**
مسافات أو أسطر جديدة في متغير DISCORD_TOKEN

**✅ الحل:**
1. اذهب إلى Render → Environment
2. تأكد من DISCORD_TOKEN **بدون**:
   - مسافات في البداية أو النهاية
   - أسطر جديدة
   - علامات اقتباس

**مثال صحيح:**
```
DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.GAbCdE.abc123
```

**مثال خاطئ:**
```
DISCORD_TOKEN= MTIzNDU2...  ← مسافة في البداية
DISCORD_TOKEN="MTIzNDU2..." ← علامات اقتباس
DISCORD_TOKEN=MTIzNDU2...
                          ← سطر جديد
```

البوت الآن ينظف هذا تلقائياً، لكن من الأفضل تصليحه في Render

---

### 3️⃣ Database Connection Failed

**الأعراض:**
```
Pool not initialized
Connection refused
```

**✅ الحلول:**

#### تحقق من DATABASE_URL
```bash
# في Render Environment، تأكد من:
DATA=postgresql://user:password@host:port/database

# ملاحظة: اسم المتغير DATA وليس DATABASE_URL
```

#### تحقق من Supabase
1. اذهب إلى Supabase Dashboard
2. Settings → Database
3. انسخ Connection String (Session mode)
4. غيّر `[YOUR-PASSWORD]` بكلمة المرور الفعلية

#### Firewall/IP Whitelist
بعض خدمات Database تحتاج IP whitelist:
1. في Supabase: اذهب Settings → Database → Connection pooling
2. أضف `0.0.0.0/0` للسماح لجميع IPs (مؤقتاً للاختبار)

---

### 4️⃣ Commands Not Syncing

**الأعراض:**
- الأوامر لا تظهر في Discord
- `/` لا يعرض الأوامر

**✅ الحلول:**

#### الحل 1: انتظر
- Discord يأخذ حتى 1 ساعة لنشر الأوامر عالمياً
- للاختبار السريع، استخدم guild-specific sync

#### الحل 2: Manual Sync
```python
# في bot.py، عدّل on_ready:
@bot.event
async def on_ready():
    # للسيرفر المحدد فقط (أسرع):
    guild = discord.Object(id=YOUR_GUILD_ID)
    tree.copy_global_to(guild=guild)
    await tree.sync(guild=guild)
```

#### الحل 3: تحقق من Intents
في Discord Developer Portal:
1. اذهب إلى Bot
2. فعّل:
   - ✅ SERVER MEMBERS INTENT
   - ✅ MESSAGE CONTENT INTENT

---

### 5️⃣ Bot Keeps Restarting

**الأعراض:**
```
♻️ Attempting to restart...
Maximum retries reached
```

**الأسباب:**
- مشكلة في Token
- مشكلة في Database
- Rate limiting

**✅ التشخيص:**
شوف الـ logs في Render:
```
📊 Total Errors: X
```

إذا كان العدد يزيد باستمرار، ابحث عن:
```
❌ خطأ في event
❌ HTTP Exception
⚠️ Rate limited
```

**الحلول:**
- إذا Rate limiting → غيّر Region أو استخدم Proxy
- إذا Database errors → تحقق من Connection String
- إذا Token errors → تحقق من صحة Token

---

### 6️⃣ Memory/CPU Issues في Render

**الأعراض:**
- البوت بطيء
- Render يعيد التشغيل تلقائياً
- "Out of memory" errors

**✅ الحلول:**

#### تقليل استهلاك الذاكرة
```python
# في bot.py:
bot = commands.Bot(
    ...
    max_messages=100,  # قلل من 1000
    chunk_guilds_at_startup=False,
    member_cache_flags=discord.MemberCacheFlags.none()
)
```

#### Upgrade Render Plan
- Free tier محدود جداً
- Starter plan ($7/month) أفضل بكثير

---

### 7️⃣ Bot in Wrong Guild

**الأعراض:**
- البوت يخرج من السيرفر تلقائياً
- "غير مصرح"

**السبب:**
`ALLOWED_GUILD_ID` مفعّل

**✅ الحلول:**

#### الحل 1: تعطيل الحماية
في Render Environment:
```
ALLOWED_GUILD_ID=    ← اتركه فارغ أو احذفه
```

#### الحل 2: تحديث Guild ID
```
ALLOWED_GUILD_ID=1234567890  ← ضع ID سيرفرك الصحيح
```

**كيف أحصل على Guild ID؟**
1. فعّل Developer Mode في Discord
2. انقر يمين على اسم السيرفر
3. Copy Server ID

---

## 🔍 أدوات التشخيص

### Check Bot Status
```bash
# في Render Logs، ابحث عن:
✅ Bot is ready!
🔒 Guild Lock: ACTIVE
📊 Total Errors: 0
```

### Check Database Connection
```bash
# ابحث عن:
✅ Database connected and tables ensured
```

### Check Slash Commands
```bash
# ابحث عن:
✅ Slash commands synced successfully
```

---

## 📞 الحصول على المساعدة

إذا جربت كل الحلول وما زالت المشكلة موجودة:

1. **جمع المعلومات:**
   - نسخ آخر 50 سطر من logs في Render
   - معلومات عن المشكلة (متى بدأت، ماذا تغير)
   - Screenshots للأخطاء

2. **تحقق من:**
   - ✅ Discord Token صحيح
   - ✅ Database URL صحيح
   - ✅ Intents مفعلة
   - ✅ Bot Permissions كافية

3. **الحلول السريعة:**
   - إعادة Deploy في Render
   - حذف وإعادة إضافة Environment Variables
   - تغيير Region في Render

---

## 🚀 Best Practices لتجنب المشاكل

### في Render:
1. ✅ استخدم Region قريب من موقعك
2. ✅ فعّل Auto-Deploy من GitHub
3. ✅ راقب Metrics بانتظام
4. ✅ احتفظ بنسخة احتياطية من Environment Variables

### في Discord:
1. ✅ فعّل جميع Intents المطلوبة
2. ✅ امنح البوت صلاحيات Administrator (للاختبار)
3. ✅ تأكد من Bot مو محظور من السيرفر

### في Database:
1. ✅ احتفظ بنسخة احتياطية يومية
2. ✅ راقب Connection Pool
3. ✅ استخدم Connection Pooling في Supabase

---

## 📊 Monitoring & Health Checks

### Logs في Render:
```bash
# ابحث بانتظام عن:
❌ # عدد الأخطاء
⚠️ # عدد التحذيرات
✅ # التأكيدات

# إذا:
❌ > 10 في الساعة → مشكلة خطيرة
⚠️ > 50 في الساعة → انتبه
```

### Database Monitoring:
- تحقق من Number of Connections
- راقب Query Performance
- تحقق من Storage Space

---

**آخر تحديث: 2024-02-01**
**الإصدار: v2.1.0 (Self-Healing)**
