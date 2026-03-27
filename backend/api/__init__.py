from fastapi import APIRouter
from .auth import router as auth_router
from .bot_triggers import router as bot_router
from .channels import router as channels_router
from .templates import router as templates_router
from .giveaways import router as giveaways_router
from .participants import router as participants_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(bot_router)
api_router.include_router(channels_router)
api_router.include_router(templates_router)
api_router.include_router(giveaways_router)
api_router.include_router(participants_router)