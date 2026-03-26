# backend/fix_alembic.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgres://postgres:cIIOIMCN55vEOZQTUNrNCX1jrnNOsVK1t6llGjeZSavHrMWuvsepbqdRgNJder41@85.239.51.64:54320/postgres"

async def fix():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        current = result.scalar()
        print(f"Текущая версия в БД: {current}")
        
        await conn.execute(text(
            "UPDATE alembic_version SET version_num = 'ba41ddde8ba7'"
        ))
        print("✅ Готово — указатель переведён на ba41ddde8ba7")
    await engine.dispose()

asyncio.run(fix())