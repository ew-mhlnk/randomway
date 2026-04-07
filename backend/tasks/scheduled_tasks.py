"""backend/tasks/scheduled_tasks.py"""
import asyncio
import logging
from datetime import datetime, timezone

from celery_app import celery
from database import AsyncSessionLocal
from repositories.giveaway_repo import giveaway_repo


@celery.task(name="tasks.scheduled_tasks.check_expired_giveaways")
def check_expired_giveaways():
    """Раз в минуту проверяет, не пора ли закрыть розыгрыш"""
    asyncio.run(_check_expired_async())


@celery.task(name="tasks.scheduled_tasks.check_pending_giveaways")
def check_pending_giveaways():
    """Раз в минуту проверяет, не пора ли запустить отложенный розыгрыш"""
    asyncio.run(_check_pending_async())


async def _check_expired_async():
    # ФИКС: убран engine.dispose()
    try:
        async with AsyncSessionLocal() as db:
            expired = await giveaway_repo.get_expired_active_giveaways(db)
            for giveaway in expired:
                logging.info(f"⏰ Время вышло! Авто-завершение розыгрыша #{giveaway.id}")
                giveaway.status = "finalizing"
                await db.commit()
                celery.send_task("tasks.giveaway_tasks.task_finalize_giveaway", args=[giveaway.id])
    except Exception as e:
        logging.error(f"check_expired_giveaways error: {e}", exc_info=True)


async def _check_pending_async():
    # НОВАЯ ЗАДАЧА: публикует розыгрыши с отложенным стартом когда пришло время
    try:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            from sqlalchemy.future import select
            from models import Giveaway
            result = await db.execute(
                select(Giveaway).where(
                    Giveaway.status == "pending",
                    Giveaway.start_date <= now,
                )
            )
            pending = result.scalars().all()

            for giveaway in pending:
                logging.info(f"🚀 Запуск отложенного розыгрыша #{giveaway.id}")
                giveaway.status = "active"
                await db.commit()
                celery.send_task("tasks.giveaway_tasks.task_publish_giveaway", args=[giveaway.id])
    except Exception as e:
        logging.error(f"check_pending_giveaways error: {e}", exc_info=True)