# db.py
# طبقة بسيطة للتعامل مع PostgreSQL باستخدام asyncpg
# إنشاء الجداول وعمليات الإدخال والاستعلام المستخدمة في البوت

import asyncpg
import asyncio

_pool: asyncpg.pool.Pool | None = None

async def init_pool(dsn: str):
    global _pool
    if _pool:
        return
    # pool صغير لكن كافٍ
    _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=4)
    return _pool

async def create_tables():
    global _pool
    if not _pool:
        raise RuntimeError("Pool not initialized")
    async with _pool.acquire() as con:
        # جدول المزادات مع دعم حالة الإلغاء
        await con.execute("""
        CREATE TABLE IF NOT EXISTS auctions (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT,
            channel_id BIGINT,
            message_id BIGINT,
            start_price BIGINT,
            current_price BIGINT,
            min_increase BIGINT,
            created_by BIGINT,
            started_at TIMESTAMP WITH TIME ZONE,
            ended_at TIMESTAMP WITH TIME ZONE,
            winner_id BIGINT,
            ended BOOLEAN DEFAULT FALSE,
            cancelled BOOLEAN DEFAULT FALSE
        );
        """)
        
        # جدول المزايدات
        await con.execute("""
        CREATE TABLE IF NOT EXISTS bids (
            id SERIAL PRIMARY KEY,
            auction_id INTEGER REFERENCES auctions(id) ON DELETE CASCADE,
            user_id BIGINT,
            amount BIGINT,
            created_at TIMESTAMP WITH TIME ZONE
        );
        """)
        
        # جدول الإعدادات
        await con.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)
        
        # إنشاء indexes لتحسين الأداء
        await con.execute("""
        CREATE INDEX IF NOT EXISTS idx_auctions_guild_id ON auctions(guild_id);
        """)
        
        await con.execute("""
        CREATE INDEX IF NOT EXISTS idx_bids_auction_id ON bids(auction_id);
        """)
    # commit done automatically

async def insert_auction(guild_id:int, channel_id:int, message_id:int, start_price:int, current_price:int, min_increase:int, created_by:int, started_at:str, ended_at:str) -> int:
    global _pool
    if not _pool:
        raise RuntimeError("Pool not initialized")
    async with _pool.acquire() as con:
        row = await con.fetchrow(
            """
            INSERT INTO auctions (guild_id, channel_id, message_id, start_price, current_price, min_increase, created_by, started_at, ended_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            RETURNING id;
            """,
            guild_id, channel_id, message_id, start_price, current_price, min_increase, created_by, started_at, ended_at
        )
        return row["id"]

async def insert_bid(auction_id:int, user_id:int, amount:int):
    global _pool
    if not _pool:
        raise RuntimeError("Pool not initialized")
    async with _pool.acquire() as con:
        await con.execute(
            """
            INSERT INTO bids (auction_id, user_id, amount, created_at)
            VALUES ($1,$2,$3, now());
            """,
            auction_id, user_id, amount
        )
        # update auction current_price
        await con.execute(
            """
            UPDATE auctions SET current_price = $1 WHERE id = $2;
            """,
            amount, auction_id
        )

async def end_auction(auction_id:int, winner_id:int|None, final_price:int|None):
    global _pool
    if not _pool:
        raise RuntimeError("Pool not initialized")
    async with _pool.acquire() as con:
        await con.execute(
            """
            UPDATE auctions SET winner_id = $1, current_price = $2, ended = TRUE, ended_at = now()
            WHERE id = $3;
            """,
            winner_id, final_price, auction_id
        )

# 🆕 دالة إلغاء المزاد
async def cancel_auction(auction_id:int):
    global _pool
    if not _pool:
        raise RuntimeError("Pool not initialized")
    async with _pool.acquire() as con:
        await con.execute(
            """
            UPDATE auctions SET cancelled = TRUE, ended = TRUE, ended_at = now()
            WHERE id = $1;
            """,
            auction_id
        )

async def get_bids_for_auction(auction_id:int):
    global _pool
    if not _pool:
        raise RuntimeError("Pool not initialized")
    async with _pool.acquire() as con:
        rows = await con.fetch(
            """
            SELECT user_id, amount, created_at FROM bids
            WHERE auction_id = $1
            ORDER BY id ASC;
            """, auction_id
        )
        return rows

# 🆕 دالة جلب سجل المزادات
async def get_auction_history(guild_id:int, limit:int = 10):
    """
    جلب سجل المزادات لسيرفر معين
    
    Args:
        guild_id: معرف السيرفر
        limit: عدد المزادات المراد جلبها
    
    Returns:
        قائمة بالمزادات مع بياناتها
    """
    global _pool
    if not _pool:
        raise RuntimeError("Pool not initialized")
    async with _pool.acquire() as con:
        rows = await con.fetch(
            """
            SELECT 
                id, 
                guild_id, 
                channel_id, 
                message_id, 
                start_price, 
                current_price, 
                min_increase, 
                created_by, 
                started_at, 
                ended_at, 
                winner_id, 
                ended, 
                cancelled
            FROM auctions
            WHERE guild_id = $1 AND ended = TRUE
            ORDER BY started_at DESC
            LIMIT $2;
            """, 
            guild_id, limit
        )
        return [dict(row) for row in rows]

# 🆕 دالة جلب إحصائيات المزاد
async def get_auction_stats(auction_id:int):
    """
    جلب إحصائيات مفصلة لمزاد معين
    
    Args:
        auction_id: معرف المزاد
    
    Returns:
        قاموس بالإحصائيات
    """
    global _pool
    if not _pool:
        raise RuntimeError("Pool not initialized")
    async with _pool.acquire() as con:
        # جلب بيانات المزاد
        auction = await con.fetchrow(
            """
            SELECT * FROM auctions WHERE id = $1;
            """, 
            auction_id
        )
        
        if not auction:
            return None
        
        # جلب عدد المزايدات
        bid_count = await con.fetchval(
            """
            SELECT COUNT(*) FROM bids WHERE auction_id = $1;
            """, 
            auction_id
        )
        
        # جلب عدد المشاركين الفريدين
        participants = await con.fetchval(
            """
            SELECT COUNT(DISTINCT user_id) FROM bids WHERE auction_id = $1;
            """, 
            auction_id
        )
        
        return {
            'auction': dict(auction),
            'total_bids': bid_count,
            'total_participants': participants
        }

# 🆕 دالة جلب إحصائيات المستخدم
async def get_user_stats(guild_id:int, user_id:int):
    """
    جلب إحصائيات مستخدم في سيرفر معين
    
    Args:
        guild_id: معرف السيرفر
        user_id: معرف المستخدم
    
    Returns:
        قاموس بالإحصائيات
    """
    global _pool
    if not _pool:
        raise RuntimeError("Pool not initialized")
    async with _pool.acquire() as con:
        # عدد المزادات الفائز بها
        wins = await con.fetchval(
            """
            SELECT COUNT(*) FROM auctions 
            WHERE guild_id = $1 AND winner_id = $2 AND ended = TRUE AND cancelled = FALSE;
            """, 
            guild_id, user_id
        )
        
        # إجمالي المبالغ المنفقة
        total_spent = await con.fetchval(
            """
            SELECT COALESCE(SUM(current_price), 0) FROM auctions 
            WHERE guild_id = $1 AND winner_id = $2 AND ended = TRUE AND cancelled = FALSE;
            """, 
            guild_id, user_id
        )
        
        # عدد المزايدات الكلية
        total_bids = await con.fetchval(
            """
            SELECT COUNT(*) FROM bids b
            JOIN auctions a ON b.auction_id = a.id
            WHERE a.guild_id = $1 AND b.user_id = $2;
            """, 
            guild_id, user_id
        )
        
        # عدد المزادات المشارك فيها
        participated_auctions = await con.fetchval(
            """
            SELECT COUNT(DISTINCT b.auction_id) FROM bids b
            JOIN auctions a ON b.auction_id = a.id
            WHERE a.guild_id = $1 AND b.user_id = $2;
            """, 
            guild_id, user_id
        )
        
        return {
            'total_wins': wins,
            'total_spent': total_spent,
            'total_bids': total_bids,
            'participated_auctions': participated_auctions
        }

# optional helpers for settings (if later تريد نقل الإعدادات إلى DB)
async def set_setting(key:str, value:str):
    global _pool
    if not _pool:
        raise RuntimeError("Pool not initialized")
    async with _pool.acquire() as con:
        await con.execute("""
        INSERT INTO settings(key,value) VALUES($1,$2)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
        """, key, value)

async def get_setting(key:str):
    global _pool
    if not _pool:
        raise RuntimeError("Pool not initialized")
    async with _pool.acquire() as con:
        row = await con.fetchrow("SELECT value FROM settings WHERE key=$1;", key)
        return row["value"] if row else None
