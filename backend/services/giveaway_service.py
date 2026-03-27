import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from repositories.giveaway_repo import giveaway_repo
from repositories.participant_repo import participant_repo
# Импортируем Celery задачи (они будут созданы в worker.py или tasks.py)
# Важно: импортировать нужно функцию задачи, которую мы вызовем через .delay()
from tasks import publish_giveaway_task, finalize_giveaway_task

class GiveawayService:
    
    # 2. Основной метод публикации
    async def publish_giveaway(self, db: AsyncSession, user_id: int, data: dict) -> int:
        """
        Создает розыгрыш и, если нужно, ставит задачу на публикацию в очередь Celery.
        """
        if not data.get('start_immediately') and not data.get('start_date'):
            raise HTTPException(status_code=400, detail="Укажите дату начала")
        
        # Создаем розыгрыш через репозиторий
        giveaway = await giveaway_repo.create(db, obj_in_data={
            "creator_id": user_id,
            "title": data['title'],
            "template_id": data['template_id'],
            "button_text": data['button_text'],
            "button_color_emoji": data['button_emoji'],
            "sponsor_channel_ids": data['sponsor_channels'],
            "publish_channel_ids": data['publish_channels'],
            "result_channel_ids": data['result_channels'],
            "start_immediately": data['start_immediately'],
            "start_date": data.get('start_date'),
            "end_date": data.get('end_date'),
            "winners_count": data['winners_count'],
            "use_boosts": data['use_boosts'],
            "use_invites": data['use_invites'],
            "max_invites": data['max_invites'],
            "use_stories": data['use_stories'],
            "use_captcha": data['use_captcha'],
            "status": "active" if data['start_immediately'] else "pending"
        })

        # Если старт немедленный — отправляем задачу в Celery
        if data['start_immediately']:
            # .delay() ставит задачу в очередь Redis
            publish_giveaway_task.delay(giveaway.id)
            logging.info(f"📦 Задача на публикацию #{giveaway.id} поставлена в очередь")

        return giveaway.id

    # Метод для получения списка розыгрышей создателя
    async def get_creator_giveaways(self, db: AsyncSession, user_id: int) -> list[dict]:
        giveaways = await giveaway_repo.get_all_by_creator(db, user_id)
        result = []
        for g in giveaways:
            p_count = await participant_repo.count_by_giveaway(db, g.id)
            result.append({
                "id": g.id,
                "title": g.title,
                "status": g.status,
                "participants_count": p_count,
                "winners_count": g.winners_count,
                "start_date": g.start_date.isoformat() if g.start_date else None,
                "end_date": g.end_date.isoformat() if g.end_date else None,
            })
        return result

    # Метод для ручного подведения итогов
    async def finalize_giveaway(self, db: AsyncSession, giveaway_id: int, user_id: int):
        """
        Проверяет права и ставит фоновую задачу подведения итогов в Celery.
        """
        giveaway = await giveaway_repo.get_active_by_id(db, giveaway_id)
        if not giveaway or giveaway.creator_id != user_id:
            raise HTTPException(status_code=400, detail="Розыгрыш не найден или уже завершен")
            
        # Ставим задачу в очередь
        finalize_giveaway_task.delay(giveaway_id)
        logging.info(f"📦 Задача на подведение итогов #{giveaway_id} поставлена в очередь")
        return {"status": "processing"}

    # Метод для поллинга статуса
    async def get_giveaway_status(self, db: AsyncSession, giveaway_id: int) -> dict:
        giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
        if not giveaway: raise HTTPException(status_code=404)
        
        winners = []
        if giveaway.status == "completed":
            winners_data = await participant_repo.get_winners_with_users(db, giveaway_id)
            winners = [{"name": u.first_name, "username": u.username} for p, u in winners_data]
            
        return {
            "status": giveaway.status,
            "winners": winners
        }


giveaway_service = GiveawayService()