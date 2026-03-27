from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from database import get_db
from models import User
from schemas import AuthRequest
from api.dependencies import validate_telegram_data

router = APIRouter(tags=["Auth"])

@router.post("/auth")
async def authenticate_user(request: AuthRequest, db: AsyncSession = Depends(get_db)):
    user_data = validate_telegram_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Неверная подпись")

    stmt = insert(User).values(
        telegram_id=user_data.get("id"),
        first_name=user_data.get("first_name", ""),
        username=user_data.get("username", ""),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["telegram_id"],
        set_=dict(first_name=stmt.excluded.first_name, username=stmt.excluded.username)
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "success", "user": user_data}