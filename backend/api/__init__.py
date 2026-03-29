"""backend/api/__init__.py"""
from fastapi import APIRouter

from api.auth import router as auth_router
from api.bot_triggers import router as bot_router
from api.channels import router as channels_router        # ← теперь FastAPI router
from api.templates import router as templates_router
from api.giveaways import router as giveaways_router
from api.participants import router as participants_router

# Все эндпоинты под /api/v1/ — согласно спеку §2.3
api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)           # POST /api/v1/auth
api_router.include_router(bot_router)            # POST /api/v1/bot/...
api_router.include_router(channels_router)       # GET/POST/DELETE /api/v1/channels/...
api_router.include_router(templates_router)      # GET/DELETE /api/v1/templates/...
api_router.include_router(giveaways_router)      # POST/GET /api/v1/giveaways/...
api_router.include_router(participants_router)   # POST /api/v1/giveaways/{id}/join