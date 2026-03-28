import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from api.dependencies import get_user_id
from database import get_db
from models import PostTemplate, Giveaway

router = APIRouter(tags=["Templates"])

def strip_html_tags(text: str) -> str:
    if not text: return ""
    text = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', text)
    return re.sub(r'<[^>]+>', '', text)

@router.get("/templates")
async def get_templates(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PostTemplate).where(PostTemplate.owner_id == user_id))
    templates = result.scalars().all()
    return {"templates":[{"id": t.id, "text": t.text, "media_type": t.media_type, "button_text": t.button_text, "button_color": t.button_color, "preview": strip_html_tags(t.text)[:120] + ("..." if len(strip_html_tags(t.text)) > 120 else "")} for t in templates]}

@router.delete("/templates/{template_id}")
async def delete_template(template_id: int, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    # 🚀 ФИКС: Проверяем, не используется ли этот шаблон в каком-нибудь розыгрыше
    linked_giveaway = await db.scalar(select(Giveaway).where(Giveaway.template_id == template_id))
    if linked_giveaway:
        raise HTTPException(status_code=400, detail="Нельзя удалить: этот шаблон используется в розыгрыше!")

    t = await db.scalar(select(PostTemplate).where(PostTemplate.id == template_id, PostTemplate.owner_id == user_id))
    if not t: raise HTTPException(status_code=404)
    
    await db.delete(t)
    await db.commit()
    return {"status": "success"}