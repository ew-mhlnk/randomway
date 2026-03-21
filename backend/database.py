import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")
DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Highload настройки:
# pool_size=20 (постоянно держим 20 соединений)
# max_overflow=10 (при пиках можем открыть еще 10, итого 30)
# pool_timeout=30 (если все 30 заняты, ждем 30 сек прежде чем выдать ошибку)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    connect_args={"statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session