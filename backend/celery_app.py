import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "randomway_tasks",
    broker=redis_url,
    backend=redis_url,
    include=["tasks.giveaway_tasks", "tasks.scheduled_tasks"]
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# 🚀 РАСПИСАНИЕ: Проверять время каждую 1 минуту
celery.conf.beat_schedule = {
    "check-expired-giveaways-every-minute": {
        "task": "tasks.scheduled_tasks.check_expired_giveaways",
        "schedule": crontab(minute="*"),
    }
}