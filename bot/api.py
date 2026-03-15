from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import urllib.parse
import hashlib
import hmac
import json
import os

router = APIRouter()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Модель для приема данных от Next.js
class AuthRequest(BaseModel):
    initData: str

def validate_telegram_data(init_data: str) -> dict | None:
    """Криптографическая проверка подписи Телеграма"""
    parsed_data = dict(urllib.parse.parse_qsl(init_data))
    if "hash" not in parsed_data:
        return None
    
    hash_val = parsed_data.pop("hash")
    # Сортируем ключи по алфавиту (требование Telegram)
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
    
    # Генерируем секретный ключ с помощью токена бота
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    # Вычисляем хеш
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    if calculated_hash == hash_val:
        # Если хеши совпали - юзер настоящий!
        return json.loads(parsed_data.get("user", "{}"))
    return None

@router.post("/auth")
async def authenticate_user(request: AuthRequest):
    user_data = validate_telegram_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Хакерская атака: неверная подпись Telegram")
    
    # В следующем шаге мы будем сохранять user_data в БД
    return {"status": "success", "user": user_data}