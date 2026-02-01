# bot.py
# السماء الجنوبية - بوت المزادات (مع Supabase/Postgres)
# كل شيء في ملف واحد رئيسي للتشغيل؛ الاعتماد على db.py للعمليات
# يتطلب: python 3.10+ (مستحسن)
# 🛡️ Self-Healing Bot مع بروتوكولات أمان

import os
import asyncio
from datetime import datetime, timezone, timedelta
import csv
from io import StringIO
import logging
import sys
import traceback
from typing import Optional
import time

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

from dotenv import load_dotenv
import json

# ملف التعامل مع قاعدة البيانات (موجود في نفس الجذر)
import db

# ---------- 🛡️ Security & Logging Setup ----------
# تكوين نظام اللوقات المحسّن
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('AuctionBot')

# 🔄 Retry Configuration
MAX_RETRIES = 5
RETRY_DELAY = 5  # ثوان
EXPONENTIAL_BACKOFF = True

# ---------- Helpers ----------
def parse_amount(text: str) -> int:
    if text is None:
        return 0
    s = str(text).strip().lower().replace(",", "")
    try:
        if s.isdigit():
            return int(s)
        if s.endswith("k"):
            return int(float(s[:-1]) * 1000)
        if s.endswith("m"):
            return int(float(s[:-1]) * 1000000)
        return int(float(s))
    except:
        return 0

def fmt_amount(n: int) -> str:
    if n is None:
        return "0"
    if n >= 1_000_000:
        v = n / 1_000_000
        if v.is_integer():
            return f"{int(v)}m"
        return f"{v:.2f}m"
    if n >= 1_000:
        v = n / 1_000
        if v.is_integer():
            return f"{int(v)}k"
        return f"{v:.1f}k"
    return str(n)

def ensure_config():
    default = {
        "auction_role_id": 0,
        "auction_channel_id": 0,
        "auction_log_channel": 0,
        "commission_percent": 20,
        "emojis": {
            "fire": "🔥",
            "crown": "🏆",
            "time": "⏳",
            "money": "💰"
        }
    }
    if not os.path.exists("config.json"):
        with open("config.json","w",encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
    with open("config.json","r",encoding="utf-8") as f:
        return json.load(f)

def load_config():
    if not os.path.exists("config.json"):
        return ensure_config()
    with open("config.json","r",encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open("config.json","w",encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ---------- env & bot setup ----------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATA")  # كما طلبت: اسم المتغير DATA
ALLOWED_GUILD_ID = os.getenv("ALLOWED_GUILD_ID")  # 🔒 ID السيرفر المسموح

# 🔧 تنظيف TOKEN من المسافات والأسطر الجديدة
if TOKEN:
    TOKEN = TOKEN.strip()
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.strip()
if ALLOWED_GUILD_ID:
    ALLOWED_GUILD_ID = ALLOWED_GUILD_ID.strip()

if not TOKEN:
    raise RuntimeError("ضع DISCORD_TOKEN في ملف .env")
if not DATABASE_URL:
    raise RuntimeError("ضع DATA (Postgres connection string) في ملف .env")

# تحويل ALLOWED_GUILD_ID إلى رقم إذا موجود
if ALLOWED_GUILD_ID:
    try:
        ALLOWED_GUILD_ID = int(ALLOWED_GUILD_ID)
        logger.info(f"🔒 وضع الحماية مفعل: السيرفر المسموح فقط ID {ALLOWED_GUILD_ID}")
    except:
        logger.warning("⚠️ ALLOWED_GUILD_ID غير صحيح، سيتم تجاهله")
        ALLOWED_GUILD_ID = None
else:
    logger.warning("⚠️ ALLOWED_GUILD_ID غير محدد، البوت سيعمل في أي سيرفر")

# 🔧 إعدادات البوت المحسّنة
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# إنشاء البوت مع معالج أخطاء محسّن
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    max_messages=1000,  # تقليل استهلاك الذاكرة
    heartbeat_timeout=60.0,  # زيادة timeout
    guild_ready_timeout=10.0
)
tree = bot.tree

# 🛡️ نظام إحصائيات الأخطاء
class ErrorStats:
    def __init__(self):
        self.errors = []
        self.last_error_time = None
        self.consecutive_errors = 0
        self.total_errors = 0
    
    def add_error(self, error_type: str):
        now = time.time()
        self.errors.append({'type': error_type, 'time': now})
        self.last_error_time = now
        self.consecutive_errors += 1
        self.total_errors += 1
        
        # احتفظ بآخر 100 خطأ فقط
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]
    
    def reset_consecutive(self):
        self.consecutive_errors = 0
    
    def should_restart(self) -> bool:
        # إعادة التشغيل إذا كان هناك أكثر من 10 أخطاء متتالية
        return self.consecutive_errors >= 10

error_stats = ErrorStats()

# ---------- In-memory cache ----------
AUCTIONS = {}  # message_id -> Auction instance

class Auction:
    def __init__(self, guild_id:int, channel_id:int, message_id:int, db_id:int, start_price:int, min_increase:int, end_time:float, created_by:int):
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.message_id = message_id
        self.db_id = db_id
        self.start_price = start_price
        self.current_price = start_price
        self.min_increase = min_increase
        self.end_time = end_time
        self.created_by = created_by
        self.highest_bidder = None
        self.bids = []  # list of tuples (timestamp_iso, user_id, amount)
        self.ended = False
        self.cancelled = False  # 🆕 حالة الإلغاء
        self.start_time = asyncio.get_event_loop().time()

    def to_log_embed(self, guild_name, emojis):
        fire = emojis.get("fire","🔥")
        crown = emojis.get("crown","🏆")
        time_emoji = emojis.get("time","⏳")
        money_emoji = emojis.get("money","💰")

        # 🆕 تحديد لون حسب حالة المزاد
        if self.cancelled:
            embed = discord.Embed(title="🚫 تقرير المزاد - تم الإلغاء", color=0xe74c3c)
        else:
            embed = discord.Embed(title="📜 تقرير المزاد الكامل", color=0x2F3136)
        
        embed.add_field(name="اسم السيرفر", value=guild_name, inline=False)
        embed.add_field(name="بداية المزاد", value=datetime.fromtimestamp(self.start_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        embed.add_field(name="نهاية المزاد", value=datetime.fromtimestamp(self.end_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        
        if self.bids:
            text = ""
            for i, bid in enumerate(self.bids, start=1):
                t_iso, uid, amt = bid
                text += f"{i}️⃣ <@{uid}> — **{fmt_amount(amt)}**\n"
            embed.add_field(name="📋 سجل المزايدات", value=text, inline=False)
        else:
            embed.add_field(name="📋 سجل المزايدات", value="لا توجد مزايدات", inline=False)
        
        participants = len(set([b[1] for b in self.bids]))
        embed.add_field(name="📊 إحصائيات", value=f"عدد المزايدات: {len(self.bids)}\nعدد المشاركين: {participants}\nأعلى مزايدة: {fmt_amount(self.current_price)}", inline=False)
        
        # 🆕 معلومات النتيجة حسب الحالة
        if self.cancelled:
            embed.add_field(name="🚫 النتيجة", value=f"**تم إلغاء المزاد**\nآخر سعر: **{fmt_amount(self.current_price)}**", inline=False)
        else:
            winner = f"<@{self.highest_bidder}>" if self.highest_bidder else "لا يوجد"
            embed.add_field(name="🏆 النتيجة", value=f"الفائز: {winner}\nالمبلغ النهائي: **{fmt_amount(self.current_price)}**", inline=False)
        
        embed.set_footer(text="السماء الجنوبية | نظام المزادات")
        return embed

# ---------- UI ----------
class BidModal(Modal, title="اكتب المبلغ"):
    amount = TextInput(label="المبلغ (مثال: 100k أو 1m أو 50000)", placeholder="مثال: 1m", required=True, max_length=20)

    def __init__(self, auction_message_id:int):
        super().__init__()
        self.auction_message_id = auction_message_id

    async def on_submit(self, interaction: discord.Interaction):
        amt = parse_amount(self.amount.value)
        auction = AUCTIONS.get(self.auction_message_id)
        if not auction or auction.ended or auction.cancelled:
            await interaction.response.send_message("المزاد غير متاح الآن.", ephemeral=True)
            return
        if interaction.user.bot:
            await interaction.response.send_message("البوت غير مسموح له بالمزايدة.", ephemeral=True)
            return
        cfg = load_config()
        role_id = cfg.get("auction_role_id", 0)
        if role_id:
            has_role = any(r.id == role_id for r in interaction.user.roles)
            if not has_role:
                await interaction.response.send_message("عذراً، لازم تكون لديك رتبة رواد المزاد لتزايد.", ephemeral=True)
                return
        min_needed = auction.current_price + auction.min_increase
        if amt < min_needed:
            await interaction.response.send_message(f"المبلغ أقل من المطلوب. الحد الأدنى التالي: {fmt_amount(min_needed)}", ephemeral=True)
            return
        # سجل في الذاكرة ثم DB
        auction.current_price = amt
        auction.highest_bidder = interaction.user.id
        ts = datetime.now(timezone.utc).isoformat()
        auction.bids.append((ts, interaction.user.id, amt))
        # سجل بالم DB
        try:
            await db.insert_bid(auction.db_id, interaction.user.id, amt)
        except Exception as e:
            print("DB insert bid error:", e)
        # تحديث الرسالة
        channel = bot.get_channel(auction.channel_id)
        try:
            msg = await channel.fetch_message(auction.message_id)
        except:
            msg = None
        if msg:
            cfg = load_config()
            emojis = cfg.get("emojis",{})
            fire = emojis.get("fire","🔥")
            embed = discord.Embed(title=f"{fire} المزاد مشتعل {fire}", color=0x9b59b6)
            embed.add_field(name="💰 السعر الحالي", value=f"**{fmt_amount(auction.current_price)}**", inline=True)
            embed.add_field(name="👑 أعلى مزايد", value=f"<@{auction.highest_bidder}>", inline=True)
            seconds_left = max(0, int(auction.end_time - asyncio.get_event_loop().time()))
            embed.add_field(name="⏳ الوقت المتبقي", value=f"{seconds_left}s", inline=False)
            embed.set_footer(text="السماء الجنوبية | نظام المزادات")
            view = msg.components[0] if msg.components else None
            await msg.edit(embed=embed, view=view)
        await interaction.response.send_message(f"تمت مزايدتك **{fmt_amount(amt)}** بنجاح!", ephemeral=True)

class AuctionView(View):
    def __init__(self, auction_message_id:int):
        super().__init__(timeout=None)
        self.auction_message_id = auction_message_id

    @discord.ui.button(label="زايد +", style=discord.ButtonStyle.primary, custom_id="quick_bid")
    async def quick_bid(self, interaction: discord.Interaction, button: Button):
        auction = AUCTIONS.get(self.auction_message_id)
        if not auction or auction.ended or auction.cancelled:
            await interaction.response.send_message("المزاد غير متاح.", ephemeral=True)
            return
        cfg = load_config()
        role_id = cfg.get("auction_role_id",0)
        if role_id:
            has_role = any(r.id == role_id for r in interaction.user.roles)
            if not has_role:
                await interaction.response.send_message("عذراً، لازم تكون لديك رتبة رواد المزاد لتزايد.", ephemeral=True)
                return
        amt = auction.current_price + auction.min_increase
        auction.current_price = amt
        auction.highest_bidder = interaction.user.id
        ts = datetime.now(timezone.utc).isoformat()
        auction.bids.append((ts, interaction.user.id, amt))
        # DB
        try:
            await db.insert_bid(auction.db_id, interaction.user.id, amt)
        except Exception as e:
            print("DB insert bid error:", e)
        # تحديث الرسالة
        channel = bot.get_channel(auction.channel_id)
        try:
            msg = await channel.fetch_message(auction.message_id)
        except:
            msg = None
        if msg:
            cfg = load_config()
            emojis = cfg.get("emojis",{})
            fire = emojis.get("fire","🔥")
            embed = discord.Embed(title=f"{fire} المزاد مشتعل {fire}", color=0x9b59b6)
            embed.add_field(name="💰 السعر الحالي", value=f"**{fmt_amount(auction.current_price)}**", inline=True)
            embed.add_field(name="👑 أعلى مزايد", value=f"<@{auction.highest_bidder}>", inline=True)
            seconds_left = max(0, int(auction.end_time - asyncio.get_event_loop().time()))
            embed.add_field(name="⏳ الوقت المتبقي", value=f"{seconds_left}s", inline=False)
            embed.set_footer(text="السماء الجنوبية | نظام المزادات")
            await msg.edit(embed=embed, view=self)
        await interaction.response.send_message(f"تمت مزايدتك **{fmt_amount(amt)}**", ephemeral=True)

    @discord.ui.button(label="مبلغ مخصّص", style=discord.ButtonStyle.secondary, custom_id="custom_bid")
    async def custom_bid(self, interaction: discord.Interaction, button: Button):
        auction = AUCTIONS.get(self.auction_message_id)
        if not auction or auction.ended or auction.cancelled:
            await interaction.response.send_message("المزاد غير متاح.", ephemeral=True)
            return
        await interaction.response.send_modal(BidModal(self.auction_message_id))

# ---------- Commands ----------
@tree.command(name="لوحة_مزاد", description="إنشاء لوحة مزايدة (إدارة فقط)")
@app_commands.describe(start="سعر البداية (مثال: 500k أو 1m)", min_inc="أقل زيادة (مثال: 50k)", duration="مدة المزاد بالدقائق", channel="قناة المزاد (اختياري)")
async def cmd_create_auction(interaction: discord.Interaction, start: str, min_inc: str, duration: int, channel: discord.TextChannel = None):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.manage_messages:
        await interaction.followup.send("أمر محظور: تحتاج صلاحيات إدارة.", ephemeral=True)
        return
    cfg = load_config()
    target_channel = channel or (bot.get_channel(cfg.get("auction_channel_id")) if cfg.get("auction_channel_id") else interaction.channel)
    if target_channel is None:
        await interaction.followup.send("لم أجد قناة لإنشاء المزاد.", ephemeral=True)
        return
    start_price = parse_amount(start)
    min_increase = parse_amount(min_inc)
    if start_price <= 0 or min_increase <= 0 or duration <= 0:
        await interaction.followup.send("المدخلات غير صحيحة.", ephemeral=True)
        return
    emojis = cfg.get("emojis",{})
    fire = emojis.get("fire","🔥")
    embed = discord.Embed(title=f"{fire} المزاد مشتعل {fire}", color=0x9b59b6)
    embed.add_field(name="💰 السعر الحالي", value=f"**{fmt_amount(start_price)}**", inline=True)
    embed.add_field(name="👑 أعلى مزايد", value="لا يوجد", inline=True)
    embed.add_field(name="⏳ الوقت المتبقي", value=f"{duration*60}s", inline=False)
    embed.set_footer(text="السماء الجنوبية | نظام المزادات")
    view = AuctionView(-1)
    msg = await target_channel.send(embed=embed, view=view)
    # إدخال المزاد في DB
    started_at = datetime.now(timezone.utc)
    end_time_dt = started_at + timedelta(minutes=duration)
    try:
        auction_db_id = await db.insert_auction(interaction.guild_id, target_channel.id, msg.id, start_price, start_price, min_increase, interaction.user.id, started_at.isoformat(), end_time_dt.isoformat())
    except Exception as e:
        print("DB insert auction error:", e)
        auction_db_id = None
    auction = Auction(guild_id=interaction.guild_id, channel_id=target_channel.id, message_id=msg.id, db_id=auction_db_id, start_price=start_price, min_increase=min_increase, end_time=asyncio.get_event_loop().time() + duration*60, created_by=interaction.user.id)
    AUCTIONS[msg.id] = auction
    view.auction_message_id = msg.id
    await msg.edit(view=view)
    # جدولة الانتهاء
    asyncio.create_task(handle_auction_end(msg.id, auction.end_time))
    await interaction.followup.send(f"تم إنشاء لوحة المزاد في {target_channel.mention}", ephemeral=True)

# 🆕 أمر إلغاء المزاد
@tree.command(name="إلغاء_مزاد", description="إلغاء مزاد نشط (إدارة فقط)")
@app_commands.describe(message_id="ID رسالة المزاد المراد إلغاؤه")
async def cmd_cancel_auction(interaction: discord.Interaction, message_id: str):
    await interaction.response.defer(ephemeral=True)
    
    # التحقق من الصلاحيات
    if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.manage_messages:
        await interaction.followup.send("أمر محظور: تحتاج صلاحيات إدارة.", ephemeral=True)
        return
    
    try:
        msg_id = int(message_id)
    except:
        await interaction.followup.send("❌ ID الرسالة غير صحيح", ephemeral=True)
        return
    
    auction = AUCTIONS.get(msg_id)
    if not auction:
        await interaction.followup.send("❌ لم أجد هذا المزاد في النظام", ephemeral=True)
        return
    
    if auction.ended or auction.cancelled:
        await interaction.followup.send("❌ المزاد منتهي أو ملغي بالفعل", ephemeral=True)
        return
    
    # وضع علامة الإلغاء
    auction.cancelled = True
    auction.ended = True
    
    # تحديث الرسالة
    channel = bot.get_channel(auction.channel_id)
    try:
        msg = await channel.fetch_message(auction.message_id)
        embed = discord.Embed(title="🚫 تم إلغاء المزاد", color=0xe74c3c)
        embed.add_field(name="السبب", value="تم الإلغاء من قبل الإدارة", inline=False)
        if auction.highest_bidder:
            embed.add_field(name="آخر مزايد", value=f"<@{auction.highest_bidder}>", inline=True)
            embed.add_field(name="آخر سعر", value=f"**{fmt_amount(auction.current_price)}**", inline=True)
        embed.set_footer(text="السماء الجنوبية | نظام المزادات")
        await msg.edit(embed=embed, view=None)
    except Exception as e:
        print(f"Error updating cancelled auction message: {e}")
    
    # تحديث قاعدة البيانات
    try:
        await db.cancel_auction(auction.db_id)
    except Exception as e:
        print(f"DB cancel auction error: {e}")
    
    # إرسال لوق
    cfg = load_config()
    log_ch = bot.get_channel(cfg.get("auction_log_channel"))
    if log_ch:
        emojis = cfg.get("emojis",{})
        full_embed = auction.to_log_embed(interaction.guild.name, emojis)
        await log_ch.send(f"⚠️ تم إلغاء المزاد بواسطة <@{interaction.user.id}>", embed=full_embed)
    
    # حذف من الذاكرة
    AUCTIONS.pop(msg_id, None)
    
    await interaction.followup.send("✅ تم إلغاء المزاد بنجاح", ephemeral=True)

# 🆕 أمر عرض سجل المزادات
@tree.command(name="سجل_المزادات", description="عرض المزادات السابقة")
@app_commands.describe(limit="عدد المزادات المراد عرضها (افتراضي: 10)")
async def cmd_auction_history(interaction: discord.Interaction, limit: int = 10):
    await interaction.response.defer(ephemeral=True)
    
    if limit < 1 or limit > 50:
        await interaction.followup.send("❌ الحد الأدنى 1 والحد الأقصى 50", ephemeral=True)
        return
    
    try:
        history = await db.get_auction_history(interaction.guild_id, limit)
        
        if not history:
            await interaction.followup.send("📭 لا توجد مزادات سابقة في هذا السيرفر", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📚 سجل المزادات",
            description=f"آخر {len(history)} مزاد في السيرفر",
            color=0x3498db
        )
        
        for i, auction_data in enumerate(history, start=1):
            auction_id = auction_data.get('id')
            started_at = auction_data.get('started_at')
            ended_at = auction_data.get('ended_at')
            winner_id = auction_data.get('winner_id')
            final_price = auction_data.get('current_price')
            cancelled = auction_data.get('cancelled', False)
            
            # تنسيق التاريخ
            if isinstance(started_at, str):
                started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            date_str = started_at.strftime("%Y-%m-%d %H:%M") if started_at else "غير محدد"
            
            # معلومات الحالة
            if cancelled:
                status = "🚫 ملغي"
                winner_str = "تم الإلغاء"
            elif winner_id:
                status = "✅ مكتمل"
                winner_str = f"<@{winner_id}>"
            else:
                status = "❌ لم يتم البيع"
                winner_str = "لا يوجد فائز"
            
            value_text = f"**التاريخ:** {date_str}\n**الحالة:** {status}\n**الفائز:** {winner_str}\n**السعر النهائي:** {fmt_amount(final_price or 0)}"
            
            embed.add_field(
                name=f"#{auction_id}",
                value=value_text,
                inline=False
            )
        
        embed.set_footer(text="السماء الجنوبية | نظام المزادات")
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        print(f"Error fetching auction history: {e}")
        await interaction.followup.send("❌ حدث خطأ أثناء جلب السجل", ephemeral=True)

# 🆕 أمر تصدير البيانات
@tree.command(name="تصدير_مزادات", description="تصدير بيانات المزادات كملف CSV (إدارة فقط)")
@app_commands.describe(limit="عدد المزادات (افتراضي: 100)")
async def cmd_export_auctions(interaction: discord.Interaction, limit: int = 100):
    await interaction.response.defer(ephemeral=True)
    
    # التحقق من الصلاحيات
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.followup.send("أمر محظور: تحتاج صلاحيات إدارة.", ephemeral=True)
        return
    
    if limit < 1 or limit > 500:
        await interaction.followup.send("❌ الحد الأدنى 1 والحد الأقصى 500", ephemeral=True)
        return
    
    try:
        # جلب البيانات
        auctions = await db.get_auction_history(interaction.guild_id, limit)
        
        if not auctions:
            await interaction.followup.send("📭 لا توجد بيانات للتصدير", ephemeral=True)
            return
        
        # إنشاء CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # الهيدر
        writer.writerow([
            'Auction ID',
            'Started At',
            'Ended At',
            'Duration (minutes)',
            'Start Price',
            'Final Price',
            'Winner ID',
            'Winner Username',
            'Creator ID',
            'Total Bids',
            'Status'
        ])
        
        # البيانات
        for auction_data in auctions:
            auction_id = auction_data.get('id')
            started_at = auction_data.get('started_at')
            ended_at = auction_data.get('ended_at')
            start_price = auction_data.get('start_price', 0)
            final_price = auction_data.get('current_price', 0)
            winner_id = auction_data.get('winner_id')
            creator_id = auction_data.get('created_by')
            cancelled = auction_data.get('cancelled', False)
            
            # حساب المدة
            duration = "N/A"
            if started_at and ended_at:
                if isinstance(started_at, str):
                    started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                if isinstance(ended_at, str):
                    ended_at = datetime.fromisoformat(ended_at.replace('Z', '+00:00'))
                duration_delta = ended_at - started_at
                duration = round(duration_delta.total_seconds() / 60, 2)
            
            # الحصول على اسم المستخدم الفائز
            winner_username = "N/A"
            if winner_id:
                try:
                    winner = await bot.fetch_user(winner_id)
                    winner_username = str(winner)
                except:
                    winner_username = f"User#{winner_id}"
            
            # جلب عدد المزايدات
            bids = await db.get_bids_for_auction(auction_id)
            total_bids = len(bids)
            
            # الحالة
            if cancelled:
                status = "Cancelled"
            elif winner_id:
                status = "Completed"
            else:
                status = "No Sale"
            
            writer.writerow([
                auction_id,
                started_at.isoformat() if started_at else "N/A",
                ended_at.isoformat() if ended_at else "N/A",
                duration,
                start_price,
                final_price,
                winner_id or "N/A",
                winner_username,
                creator_id or "N/A",
                total_bids,
                status
            ])
        
        # تحويل إلى ملف
        output.seek(0)
        file = discord.File(
            fp=output,
            filename=f"auctions_export_{interaction.guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        await interaction.followup.send(
            f"✅ تم تصدير {len(auctions)} مزاد",
            file=file,
            ephemeral=True
        )
        
    except Exception as e:
        print(f"Error exporting auctions: {e}")
        await interaction.followup.send("❌ حدث خطأ أثناء التصدير", ephemeral=True)

@tree.command(name="set_auction_role", description="تحديد رتبة رواد المزاد (إداري فقط)")
@app_commands.describe(role="رتبة الرواد")
async def cmd_set_role(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("تحتاج صلاحيات إدارة.", ephemeral=True); return
    cfg = load_config()
    cfg["auction_role_id"] = role.id
    save_config(cfg)
    await interaction.response.send_message(f"تم تحديد رتبة رواد المزاد: {role.name}", ephemeral=True)

@tree.command(name="set_auction_channel", description="تحديد قناة المزادات الافتراضية")
@app_commands.describe(channel="قناة المزاد")
async def cmd_set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("تحتاج صلاحيات إدارة.", ephemeral=True); return
    cfg = load_config()
    cfg["auction_channel_id"] = channel.id
    save_config(cfg)
    await interaction.response.send_message(f"تم تحديد قناة المزاد: {channel.mention}", ephemeral=True)

@tree.command(name="set_log_channel", description="تحديد قناة اللوق للمزادات")
@app_commands.describe(channel="قناة اللوق")
async def cmd_set_log(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("تحتاج صلاحيات إدارة.", ephemeral=True); return
    cfg = load_config()
    cfg["auction_log_channel"] = channel.id
    save_config(cfg)
    await interaction.response.send_message(f"تم تحديد قناة اللوق: {channel.mention}", ephemeral=True)

@tree.command(name="set_emoji", description="تعيين ايموجي مخصص لنوع معين")
@app_commands.describe(key="النوع (fire,crown,time,money)", emoji="ايموجي السيرفر (مثال: <:fire_south:123>)")
async def cmd_set_emoji(interaction: discord.Interaction, key: str, emoji: str):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("تحتاج صلاحيات إدارة.", ephemeral=True); return
    key = key.strip()
    if key not in ("fire","crown","time","money"):
        await interaction.response.send_message("الأنواع المتاحة: fire, crown, time, money", ephemeral=True); return
    cfg = load_config()
    cfg.setdefault("emojis", {})
    cfg["emojis"][key] = emoji
    save_config(cfg)
    await interaction.response.send_message(f"تم حفظ الايموجي للنوع `{key}`", ephemeral=True)

# ---------- Auction end handler ----------
async def handle_auction_end(message_id:int, end_time:float):
    now = asyncio.get_event_loop().time()
    wait = end_time - now
    if wait > 0:
        await asyncio.sleep(wait)
    auction = AUCTIONS.get(message_id)
    if not auction or auction.ended:
        return
    auction.ended = True
    channel = bot.get_channel(auction.channel_id)
    try:
        msg = await channel.fetch_message(auction.message_id)
    except:
        msg = None
    if msg:
        cfg = load_config()
        emojis = cfg.get("emojis",{})
        crown = emojis.get("crown","🏆")
        embed = discord.Embed(title=f"{crown} انتهى المزاد {crown}", color=0x95a5a6)
        winner_text = f"<@{auction.highest_bidder}>" if auction.highest_bidder else "لم يتم البيع"
        embed.add_field(name="🏆 الفائز", value=winner_text, inline=True)
        embed.add_field(name="💰 السعر النهائي", value=f"**{fmt_amount(auction.current_price)}**", inline=True)
        embed.set_footer(text="السماء الجنوبية | نظام المزادات")
        await msg.edit(embed=embed, view=None)
    # حفظ النتيجة في DB
    try:
        await db.end_auction(auction.db_id, auction.highest_bidder, auction.current_price)
    except Exception as e:
        print("DB end auction error:", e)
    # ارسال لوق مفصل
    cfg = load_config()
    log_ch = bot.get_channel(cfg.get("auction_log_channel"))
    if log_ch:
        emojis = cfg.get("emojis",{})
        full_embed = auction.to_log_embed(bot.get_guild(auction.guild_id).name, emojis)
        await log_ch.send(embed=full_embed)
    # أزل المزاد من الذاكرة بعد القليل
    await asyncio.sleep(5)
    AUCTIONS.pop(message_id, None)

# ---------- Events ----------
# 🛡️ معالج الأخطاء العام
@bot.event
async def on_error(event: str, *args, **kwargs):
    error_stats.add_error(event)
    logger.error(f"❌ خطأ في event {event}: {traceback.format_exc()}")
    
    # إذا كانت الأخطاء كثيرة، جرب إعادة الاتصال
    if error_stats.should_restart():
        logger.critical("⚠️ أخطاء كثيرة متتالية! محاولة إعادة الاتصال...")
        error_stats.reset_consecutive()
        try:
            await bot.close()
            await asyncio.sleep(10)
        except:
            pass

# 🔄 معالج قطع الاتصال
@bot.event
async def on_disconnect():
    logger.warning("⚠️ تم قطع الاتصال بـ Discord")
    error_stats.add_error('disconnect')

# ✅ معالج استئناف الاتصال
@bot.event
async def on_resumed():
    logger.info("✅ تم استئناف الاتصال بـ Discord بنجاح")
    error_stats.reset_consecutive()

# 🔒 حماية السيرفر - الخروج من السيرفرات غير المسموحة
@bot.event
async def on_guild_join(guild: discord.Guild):
    if ALLOWED_GUILD_ID and guild.id != ALLOWED_GUILD_ID:
        logger.warning(f"🚫 Attempted to join unauthorized guild: {guild.name} (ID: {guild.id})")
        logger.info(f"🚪 Leaving guild immediately...")
        
        # محاولة إرسال رسالة للسيرفر قبل المغادرة (اختياري)
        try:
            # البحث عن قناة عامة لإرسال رسالة
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    embed = discord.Embed(
                        title="🚫 غير مصرح",
                        description="عذراً، هذا البوت خاص ومقتصر على سيرفر معين فقط.",
                        color=0xe74c3c
                    )
                    embed.add_field(name="السبب", value="البوت مُقفل على سيرفر محدد", inline=False)
                    embed.set_footer(text="السماء الجنوبية | نظام المزادات")
                    await channel.send(embed=embed)
                    break
        except Exception as e:
            logger.error(f"Could not send message before leaving: {e}")
        
        # المغادرة من السيرفر
        await guild.leave()
        logger.info(f"✅ Successfully left guild: {guild.name}")

@bot.event
async def on_ready():
    """
    🚀 Event يتم استدعاؤه عند اتصال البوت بنجاح
    """
    try:
        # init DB pool
        logger.info("🔌 Connecting to database...")
        await db.init_pool(os.getenv("DATA"))
        await db.create_tables()
        logger.info("✅ Database connected and tables ensured")
        
        # 🔒 التحقق من السيرفرات الحالية
        if ALLOWED_GUILD_ID:
            logger.info(f"🔒 Checking current guilds against allowed guild ID: {ALLOWED_GUILD_ID}")
            guilds_to_leave = []
            
            for guild in bot.guilds:
                if guild.id != ALLOWED_GUILD_ID:
                    logger.warning(f"🚫 Found unauthorized guild: {guild.name} (ID: {guild.id})")
                    guilds_to_leave.append(guild)
                else:
                    logger.info(f"✅ Authorized guild found: {guild.name} (ID: {guild.id})")
            
            # المغادرة من السيرفرات غير المصرح بها
            for guild in guilds_to_leave:
                try:
                    logger.info(f"🚪 Leaving unauthorized guild: {guild.name}")
                    await guild.leave()
                    logger.info(f"✅ Successfully left: {guild.name}")
                except Exception as e:
                    logger.error(f"❌ Error leaving guild {guild.name}: {e}")
            
            if guilds_to_leave:
                logger.info(f"🧹 Cleaned up {len(guilds_to_leave)} unauthorized guild(s)")
        
        # مزامنة الأوامر
        try:
            logger.info("🔄 Syncing slash commands...")
            await tree.sync()
            logger.info("✅ Slash commands synced successfully")
            error_stats.reset_consecutive()  # إعادة تعيين عداد الأخطاء عند النجاح
        except Exception as e:
            logger.error(f"❌ Sync error: {e}")
            error_stats.add_error('sync_failed')
        
        # طباعة معلومات البوت
        logger.info("=" * 50)
        logger.info("✅ Bot is ready and operational!")
        logger.info(f"👤 Logged in as: {bot.user} (ID: {bot.user.id})")
        logger.info(f"🗄️  Database: Connected")
        logger.info(f"🌐 Guilds: {len(bot.guilds)}")
        if ALLOWED_GUILD_ID:
            logger.info(f"🔒 Guild Lock: ACTIVE (ID: {ALLOWED_GUILD_ID})")
        else:
            logger.warning(f"⚠️  Guild Lock: DISABLED")
        logger.info(f"📊 Total Errors: {error_stats.total_errors}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.critical(f"❌ Critical error in on_ready: {e}")
        logger.critical(traceback.format_exc())
        error_stats.add_error('on_ready_failed')

# ---------- keep alive ----------
try:
    from web import keep_alive
    keep_alive()
    logger.info("✅ Web server started for keep-alive")
except Exception as e:
    logger.warning(f"⚠️ Web keep alive not started: {e}")

# ---------- 🛡️ Self-Healing Run with Retry Logic ----------
async def run_bot_with_retry():
    """
    تشغيل البوت مع نظام إعادة المحاولة التلقائي
    """
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            logger.info(f"🚀 Starting bot... (Attempt {retry_count + 1}/{MAX_RETRIES})")
            
            # تشغيل البوت
            async with bot:
                await bot.start(TOKEN)
                
        except discord.LoginFailure as e:
            logger.critical(f"❌ LOGIN FAILED: Invalid Discord token!")
            logger.critical(f"Error: {e}")
            logger.critical("Please check your DISCORD_TOKEN in environment variables")
            break  # لا نعيد المحاولة إذا كان الـ Token خاطئ
            
        except discord.HTTPException as e:
            retry_count += 1
            
            if e.status == 429:  # Rate limited
                logger.warning(f"⚠️ Rate limited by Discord! Status: {e.status}")
                wait_time = RETRY_DELAY * (2 ** retry_count if EXPONENTIAL_BACKOFF else 1)
                logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
                
            elif e.status in [502, 503, 504]:  # Server errors
                logger.warning(f"⚠️ Discord server error: {e.status}")
                wait_time = RETRY_DELAY * (2 ** retry_count if EXPONENTIAL_BACKOFF else 1)
                logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
                
            else:
                logger.error(f"❌ HTTP Exception: {e}")
                wait_time = RETRY_DELAY * 2
                logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
                
        except discord.ConnectionClosed as e:
            retry_count += 1
            logger.warning(f"⚠️ Connection closed: {e}")
            wait_time = RETRY_DELAY * (2 ** retry_count if EXPONENTIAL_BACKOFF else 1)
            logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            retry_count += 1
            logger.error(f"❌ Unexpected error: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_DELAY * (2 ** retry_count if EXPONENTIAL_BACKOFF else 1)
                logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
            else:
                logger.critical("❌ Maximum retries reached. Stopping bot.")
                break
        
        # إذا وصلنا هنا، يعني البوت توقف بشكل طبيعي
        if retry_count == 0:
            logger.info("✅ Bot stopped normally")
            break
        else:
            logger.info(f"♻️ Attempting to restart... (Attempt {retry_count + 1}/{MAX_RETRIES})")
    
    logger.info("🛑 Bot shutdown complete")

# ---------- Run ----------
if __name__ == "__main__":
    try:
        # التأكد من وجود الـ Token
        if not TOKEN or len(TOKEN) < 50:
            logger.critical("❌ CRITICAL: Invalid or missing DISCORD_TOKEN")
            logger.critical("Please check your environment variables in Render")
            logger.critical(f"Token length: {len(TOKEN) if TOKEN else 0}")
            sys.exit(1)
        
        logger.info("=" * 50)
        logger.info("🤖 AuctionBot - السماء الجنوبية")
        logger.info("🛡️ Self-Healing System Active")
        logger.info("=" * 50)
        
        # تشغيل البوت مع نظام إعادة المحاولة
        asyncio.run(run_bot_with_retry())
        
    except KeyboardInterrupt:
        logger.info("⚠️ Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"❌ FATAL ERROR: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
