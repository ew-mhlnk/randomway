import asyncio
import logging
from celery_app import celery
from database import engine
from services.giveaway_service import giveaway_service

@celery.task(name="tasks.giveaway_tasks.task_publish_giveaway")
def task_publish_giveaway(giveaway_id: int):
    """Celery-задача для рассылки поста по каналам"""
    logging.info(f"CELERY: Запуск публикации для розыгрыша {giveaway_id}")
    asyncio.run(_run_publish(giveaway_id))
    return f"Published {giveaway_id}"

@celery.task(name="tasks.giveaway_tasks.task_finalize_giveaway")
def task_finalize_giveaway(giveaway_id: int):
    """Celery-задача для подведения итогов и рулетки"""
    logging.info(f"CELERY: Подведение итогов для розыгрыша {giveaway_id}")
    asyncio.run(_run_finalize(giveaway_id))
    return f"Finalized {giveaway_id}"

# --- Асинхронные обертки с защитой базы данных ---

async def _run_publish(giveaway_id: int):
    try:
        await giveaway_service._post_to_channels_task(giveaway_id)
    finally:
        # 🚀 Сбрасываем пул соединений
        await engine.dispose()

async def _run_finalize(giveaway_id: int):
    try:
        await giveaway_service._finalize_giveaway_task(giveaway_id)
    finally:
        # 🚀 Сбрасываем пул соединений
        await engine.dispose()