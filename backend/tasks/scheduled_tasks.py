import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.future import select
from celery_app import celery
from database import DATABASE_URL
from models import Giveaway

@celery.task(name="tasks.scheduled_tasks.check_expired_giveaways")
def check_expired_giveaways():
    asyncio.run(_check_expired_async())

@celery.task(name="tasks.scheduled_tasks.check_pending_giveaways")
def check_pending_giveaways():
    asyncio.run(_check_pending_async())

async def _check_expired_async():
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        async with SessionLocal() as db:
            now = datetime.now(timezone.utc)
            expired = (await db.execute(select(Giveaway).where(Giveaway.status == "active", Giveaway.end_date <= now))).scalars().all()
            for gw in expired:
                gw.status = "finalizing"
                await db.commit()
                celery.send_task("tasks.giveaway_tasks.task_finalize_giveaway", args=[gw.id])
    finally:
        await engine.dispose()

async def _check_pending_async():
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        async with SessionLocal() as db:
            now = datetime.now(timezone.utc)
            pending = (await db.execute(select(Giveaway).where(Giveaway.status == "pending", Giveaway.start_date <= now))).scalars().all()
            for gw in pending:
                gw.status = "active"
                await db.commit()
                celery.send_task("tasks.giveaway_tasks.task_publish_giveaway", args=[gw.id])
    finally:
        await engine.dispose()