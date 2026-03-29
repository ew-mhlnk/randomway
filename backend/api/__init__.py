from fastapi import APIRouter

from api.auth import router as auth_router
from api.bot_triggers import router as bot_router
from api.channels import router as channels_router
from api.templates import router as templates_router
from api.giveaways import router as giveaways_router
from api.participants import router as participants_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(bot_router)
api_router.include_router(channels_router)
api_router.include_router(templates_router)
api_router.include_router(giveaways_router)
api_router.include_router(participants_router)