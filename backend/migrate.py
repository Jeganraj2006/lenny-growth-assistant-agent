import asyncio
from sqlalchemy import text
from app.db.session import engine

async def migrate():
    print("Running database column migration...")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.execute(text("ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS citations JSONB DEFAULT '[]'::jsonb;"))
    print("Migration complete: citations column added to artifacts table.")

if __name__ == "__main__":
    asyncio.run(migrate())
