import asyncio
import logging
from celery_app import celery
from database import AsyncSessionLocal
from repositories.giveaway_repo import giveaway_repo

@celery.task(name="tasks.scheduled_tasks.check_expired_giveaways")
def check_expired_giveaways():
    """Раз в минуту проверяет, не пора ли закрыть розыгрыш"""
    asyncio.run(_check_async())

async def _check_async():
    async with AsyncSessionLocal() as db:
        # Достаем все активные розыгрыши, у которых вышло время
        expired = await giveaway_repo.get_expired_active_giveaways(db)
        
        for giveaway in expired:
            logging.info(f"⏰ Время вышло! Авто-завершение розыгрыша #{giveaway.id}")
            
            # Меняем статус, чтобы юзеры больше не могли зайти
            giveaway.status = "finalizing"
            await db.commit()
            
            # 🚀 Передаем задачу Воркеру (по имени, чтобы не было ошибок импорта)
            celery.send_task("tasks.giveaway_tasks.task_finalize_giveaway", args=[giveaway.id])