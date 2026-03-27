import os
import hmac
import hashlib
import urllib.parse
import json
import time
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()
BOT_TOKEN = os.getenv("BOT_TOKEN")

def validate_telegram_data(init_data: str) -> dict | None:
    parsed_data = dict(urllib.parse.parse_qsl(init_data))
    if "hash" not in parsed_data:
        return None
    hash_val = parsed_data.pop("hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if calculated_hash == hash_val:
        auth_date = int(parsed_data.get("auth_date", 0))
        if time.time() - auth_date > 86400: # Токен живет 24 часа
            return None
        return json.loads(parsed_data.get("user", "{}"))
    return None

def get_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    user_data = validate_telegram_data(credentials.credentials)
    if not user_data:
        raise HTTPException(status_code=401, detail="Неверная подпись Telegram")
    return user_data["id"]