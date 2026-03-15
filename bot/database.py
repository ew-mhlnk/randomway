import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# Делаем пуленепробиваемую замену префиксов URL
DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")
DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Создаем движок
engine = create_async_engine(DATABASE_URL, echo=False)

# Создаем фабрику сессий
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# Базовый класс для всех моделей
class Base(AsyncAttrs, DeclarativeBase):
    pass

# Dependency для FastAPI (будем использовать позже)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session