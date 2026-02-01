#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗄️ Database Layer - AuctionBot
معالجة قاعدة البيانات PostgreSQL باستخدام asyncpg

المطور: دارك
النسخة: 3.0.0
"""

import asyncpg
from typing import Optional, List, Dict

# Connection Pool
_pool: Optional[asyncpg.pool.Pool] = None

async def init_pool(dsn: str):
    """إنشاء connection pool"""
    global _pool
    if _pool:
        return _pool
    
    _pool = await asyncpg.create_pool(
        dsn,
        min_size=1,
        max_size=10,
        command_timeout=60
    )
    return _pool

async def create_tables():
    """إنشاء الجداول المطلوبة"""
    global _pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    
    async with _pool.acquire() as conn:
        # جدول المزادات
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS auctions (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                message_id BIGINT NOT NULL,
                start_price BIGINT NOT NULL,
                current_price BIGINT NOT NULL,
                min_increase BIGINT NOT NULL,
                created_by BIGINT NOT NULL,
                started_at TIMESTAMP WITH TIME ZONE NOT NULL,
                ended_at TIMESTAMP WITH TIME ZONE,
                winner_id BIGINT,
                ended BOOLEAN DEFAULT FALSE,
                cancelled BOOLEAN DEFAULT FALSE
            );
        """)
        
        # جدول المزايدات
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bids (
                id SERIAL PRIMARY KEY,
                auction_id INTEGER NOT NULL REFERENCES auctions(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL,
                amount BIGINT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # Indexes لتحسين الأداء
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_auctions_guild_id 
            ON auctions(guild_id);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_auctions_message_id 
            ON auctions(message_id);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bids_auction_id 
            ON bids(auction_id);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bids_user_id 
            ON bids(user_id);
        """)

# ==================== AUCTION OPERATIONS ====================

async def insert_auction(
    guild_id: int,
    channel_id: int,
    message_id: int,
    start_price: int,
    current_price: int,
    min_increase: int,
    created_by: int,
    started_at: str,
    ended_at: str
) -> int:
    """إدخال مزاد جديد"""
    global _pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO auctions (
                guild_id, channel_id, message_id, start_price,
                current_price, min_increase, created_by,
                started_at, ended_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id;
            """,
            guild_id, channel_id, message_id, start_price,
            current_price, min_increase, created_by,
            started_at, ended_at
        )
        return row['id']

async def end_auction(auction_id: int, winner_id: Optional[int], final_price: Optional[int]):
    """إنهاء مزاد"""
    global _pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE auctions
            SET winner_id = $1, current_price = $2, ended = TRUE, ended_at = NOW()
            WHERE id = $3;
            """,
            winner_id, final_price, auction_id
        )

async def cancel_auction(auction_id: int):
    """إلغاء مزاد"""
    global _pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE auctions
            SET cancelled = TRUE, ended = TRUE, ended_at = NOW()
            WHERE id = $1;
            """,
            auction_id
        )

async def get_auction_history(guild_id: int, limit: int = 10) -> List[Dict]:
    """جلب سجل المزادات"""
    global _pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT 
                id, guild_id, channel_id, message_id,
                start_price, current_price, min_increase,
                created_by, started_at, ended_at,
                winner_id, ended, cancelled
            FROM auctions
            WHERE guild_id = $1 AND ended = TRUE
            ORDER BY started_at DESC
            LIMIT $2;
            """,
            guild_id, limit
        )
        return [dict(row) for row in rows]

# ==================== BID OPERATIONS ====================

async def insert_bid(auction_id: int, user_id: int, amount: int):
    """إدخال مزايدة جديدة"""
    global _pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    
    async with _pool.acquire() as conn:
        # إدخال المزايدة
        await conn.execute(
            """
            INSERT INTO bids (auction_id, user_id, amount, created_at)
            VALUES ($1, $2, $3, NOW());
            """,
            auction_id, user_id, amount
        )
        
        # تحديث سعر المزاد
        await conn.execute(
            """
            UPDATE auctions
            SET current_price = $1
            WHERE id = $2;
            """,
            amount, auction_id
        )

async def get_bids_for_auction(auction_id: int) -> List[Dict]:
    """جلب مزايدات مزاد معين"""
    global _pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT user_id, amount, created_at
            FROM bids
            WHERE auction_id = $1
            ORDER BY created_at ASC;
            """,
            auction_id
        )
        return [dict(row) for row in rows]

# ==================== STATS & ANALYTICS ====================

async def get_auction_stats(auction_id: int) -> Optional[Dict]:
    """إحصائيات مزاد معين"""
    global _pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    
    async with _pool.acquire() as conn:
        # بيانات المزاد
        auction = await conn.fetchrow(
            "SELECT * FROM auctions WHERE id = $1;",
            auction_id
        )
        
        if not auction:
            return None
        
        # عدد المزايدات
        bid_count = await conn.fetchval(
            "SELECT COUNT(*) FROM bids WHERE auction_id = $1;",
            auction_id
        )
        
        # عدد المشاركين
        participants = await conn.fetchval(
            "SELECT COUNT(DISTINCT user_id) FROM bids WHERE auction_id = $1;",
            auction_id
        )
        
        return {
            'auction': dict(auction),
            'total_bids': bid_count,
            'total_participants': participants
        }

async def get_user_stats(guild_id: int, user_id: int) -> Dict:
    """إحصائيات مستخدم"""
    global _pool
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    
    async with _pool.acquire() as conn:
        # عدد الانتصارات
        wins = await conn.fetchval(
            """
            SELECT COUNT(*) FROM auctions
            WHERE guild_id = $1 AND winner_id = $2
            AND ended = TRUE AND cancelled = FALSE;
            """,
            guild_id, user_id
        )
        
        # إجمالي المبالغ
        total_spent = await conn.fetchval(
            """
            SELECT COALESCE(SUM(current_price), 0) FROM auctions
            WHERE guild_id = $1 AND winner_id = $2
            AND ended = TRUE AND cancelled = FALSE;
            """,
            guild_id, user_id
        )
        
        # عدد المزايدات
        total_bids = await conn.fetchval(
            """
            SELECT COUNT(*) FROM bids b
            JOIN auctions a ON b.auction_id = a.id
            WHERE a.guild_id = $1 AND b.user_id = $2;
            """,
            guild_id, user_id
        )
        
        # المزادات المشارك فيها
        participated = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT b.auction_id) FROM bids b
            JOIN auctions a ON b.auction_id = a.id
            WHERE a.guild_id = $1 AND b.user_id = $2;
            """,
            guild_id, user_id
        )
        
        return {
            'total_wins': wins or 0,
            'total_spent': total_spent or 0,
            'total_bids': total_bids or 0,
            'participated_auctions': participated or 0
        }

# ==================== CLEANUP ====================

async def close_pool():
    """إغلاق connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
