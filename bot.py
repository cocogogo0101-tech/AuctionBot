# bot.py
# السماء الجنوبية - بوت المزادات (مع Supabase/Postgres)
# كل شيء في ملف واحد رئيسي للتشغيل؛ الاعتماد على db.py للعمليات
# يتطلب: python 3.10+ (مستحسن)

import os
import asyncio
from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

from dotenv import load_dotenv
import json

# ملف التعامل مع قاعدة البيانات (موجود في نفس الجذر)
import db

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

if not TOKEN:
    raise RuntimeError("ضع DISCORD_TOKEN في ملف .env")
if not DATABASE_URL:
    raise RuntimeError("ضع DATA (Postgres connection string) في ملف .env")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
tree = bot.tree

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
        self.start_time = asyncio.get_event_loop().time()

    def to_log_embed(self, guild_name, emojis):
        fire = emojis.get("fire","🔥")
        crown = emojis.get("crown","🏆")
        time_emoji = emojis.get("time","⏳")
        money_emoji = emojis.get("money","💰")

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
        if not auction or auction.ended:
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
        if not auction or auction.ended:
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
        if not auction or auction.ended:
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
@bot.event
async def on_ready():
    # init DB pool
    await db.init_pool(os.getenv("DATA"))
    await db.create_tables()
    try:
        await tree.sync()
    except Exception as e:
        print("sync error:", e)
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("DB pool ready and tables ensured.")

# ---------- keep alive ----------
try:
    from web import keep_alive
    keep_alive()
except Exception as e:
    print("web keep alive not started:", e)

# ---------- Run ----------
if __name__ == "__main__":
    bot.run(TOKEN)