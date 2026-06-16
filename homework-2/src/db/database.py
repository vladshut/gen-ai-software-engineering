import os
import aiosqlite
from contextlib import asynccontextmanager

DB_PATH = os.environ.get("DATABASE_URL", "tickets.db")


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        yield conn


async def init_db():
    async with get_db() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'new',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT,
                assigned_to TEXT,
                tags TEXT DEFAULT '[]',
                source TEXT DEFAULT 'api',
                browser TEXT,
                device_type TEXT
            )
            """
        )
        await conn.commit()
