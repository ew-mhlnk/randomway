import asyncio
import logging
from celery_app import celery  # ок если запускается из backend/

# Импортируем нашу логику из сервиса
from services.giveaway_service import giveaway_service

@celery.task(name="tasks.giveaway_tasks.publish_giveaway")
def task_publish_giveaway(giveaway_id: int):
    """Celery-задача для рассылки поста по каналам"""
    logging.info(f"CELERY: Запуск публикации для розыгрыша {giveaway_id}")
    asyncio.run(giveaway_service._post_to_channels_task(giveaway_id))
    return f"Published {giveaway_id}"

@celery.task(name="tasks.giveaway_tasks.finalize_giveaway")
def task_finalize_giveaway(giveaway_id: int):
    """Celery-задача для подведения итогов и рулетки"""
    logging.info(f"CELERY: Подведение итогов для розыгрыша {giveaway_id}")
    asyncio.run(giveaway_service._finalize_giveaway_task(giveaway_id))
    return f"Finalized {giveaway_id}"