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
            ended BOOLEAN DEFAULT FALSE
        );
        """)
        await con.execute("""
        CREATE TABLE IF NOT EXISTS bids (
            id SERIAL PRIMARY KEY,
            auction_id INTEGER REFERENCES auctions(id) ON DELETE CASCADE,
            user_id BIGINT,
            amount BIGINT,
            created_at TIMESTAMP WITH TIME ZONE
        );
        """)
        await con.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
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