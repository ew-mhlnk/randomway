import asyncio
import logging
from celery_app import celery
from database import AsyncSessionLocal, engine
from repositories.giveaway_repo import giveaway_repo

@celery.task(name="tasks.scheduled_tasks.check_expired_giveaways")
def check_expired_giveaways():
    """Раз в минуту проверяет, не пора ли закрыть розыгрыш"""
    asyncio.run(_check_async())

async def _check_async():
    try:
        async with AsyncSessionLocal() as db:
            # Достаем все активные розыгрыши, у которых вышло время
            expired = await giveaway_repo.get_expired_active_giveaways(db)
            
            for giveaway in expired:
                logging.info(f"⏰ Время вышло! Авто-завершение розыгрыша #{giveaway.id}")
                giveaway.status = "finalizing"
                await db.commit()
                
                # Отправляем задачу Воркеру (по имени)
                celery.send_task("tasks.giveaway_tasks.task_finalize_giveaway", args=[giveaway.id])
    finally:
        # 🚀 ВОТ ОН ФИКС: Сбрасываем пул соединений БД после завершения задачи!
        await engine.dispose()