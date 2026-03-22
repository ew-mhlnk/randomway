import os
import aiohttp
import aioboto3
import logging
import asyncio
from botocore.config import Config

BOT_TOKEN = os.getenv("BOT_TOKEN")
S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL")
S3_ACCESS = os.getenv("S3_ACCESS_KEY")
S3_SECRET = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_PUBLIC = os.getenv("S3_PUBLIC_URL")

# 🔥 ГЛОБАЛЬНАЯ СЕССИЯ. Запрещено создавать aioboto3.Session() внутри async-функций!
# Это синхронно читает JSON с диска и вешает весь FastAPI event loop.
global_s3_session = aioboto3.Session()

async def upload_tg_avatar_to_s3(file_id: str, channel_id: int) -> str | None:
    if not all([S3_ENDPOINT, S3_ACCESS, S3_SECRET, S3_BUCKET]):
        return None

    try:
        return await asyncio.wait_for(_upload_internal(file_id, channel_id), timeout=8.0)
    except Exception as e:
        logging.error(f"S3 Upload Error/Timeout: {e}")
        return None

async def _upload_internal(file_id: str, channel_id: int) -> str | None:
    async with aiohttp.ClientSession() as session:
        # Скачиваем путь
        async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}") as r:
            data = await r.json()
            if not data.get("ok"): return None
            file_path = data["result"]["file_path"]

        # Скачиваем файл
        async with session.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}") as r:
            file_bytes = await r.read()
            content_type = r.headers.get("Content-Type", "image/jpeg")

    file_ext = "jpg" if "jpeg" in content_type else "png"
    object_name = f"avatars/channel_{channel_id}.{file_ext}"

    # Настройки таймаутов для самого boto3, чтобы не ждал вечность
    config = Config(
        signature_version='s3v4',
        connect_timeout=2,
        read_timeout=3,
        retries={'max_attempts': 1}
    )
    
    async with global_s3_session.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        region_name="auto",
        config=config
    ) as s3_client:
        await s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=object_name,
            Body=file_bytes,
            ContentType=content_type
        )

    return f"{S3_PUBLIC}/{object_name}"