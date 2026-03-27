from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_user_id
from database import get_db
from schemas import JoinGiveawayRequest
from services.participant_service import participant_service

router = APIRouter(tags=["Participants"])

@router.post("/giveaways/{giveaway_id}/join")
async def join_giveaway(
    giveaway_id: int,
    request: Request,
    payload: JoinGiveawayRequest,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    bot = request.app.state.bot
    return await participant_service.join_giveaway(
        db=db, bot=bot, giveaway_id=giveaway_id, user_id=user_id, ref_code=payload.ref_code
    )