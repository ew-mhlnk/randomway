import os
import aiohttp
import aioboto3
import logging
from botocore.config import Config

BOT_TOKEN = os.getenv("BOT_TOKEN")
S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL")
S3_ACCESS = os.getenv("S3_ACCESS_KEY")
S3_SECRET = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_PUBLIC = os.getenv("S3_PUBLIC_URL")

async def upload_tg_avatar_to_s3(file_id: str, channel_id: int) -> str | None:
    if not all([S3_ENDPOINT, S3_ACCESS, S3_SECRET, S3_BUCKET]):
        logging.error("S3 credentials не найдены в .env!")
        return None

    try:
        # 1. Спрашиваем у Телеграма путь к файлу
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}") as r:
                data = await r.json()
                if not data.get("ok"): return None
                file_path = data["result"]["file_path"]

            # 2. Скачиваем сам файл
            async with session.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}") as r:
                file_bytes = await r.read()
                content_type = r.headers.get("Content-Type", "image/jpeg")

        # 3. Загружаем в Cloudflare R2
        file_ext = "jpg" if "jpeg" in content_type else "png"
        object_name = f"avatars/channel_{channel_id}.{file_ext}"

        s3_session = aioboto3.Session()
        config = Config(signature_version='s3v4')
        
        async with s3_session.client(
            's3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS,
            aws_secret_access_key=S3_SECRET,
            config=config
        ) as s3_client:
            await s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=object_name,
                Body=file_bytes,
                ContentType=content_type
            )

        # Возвращаем готовую публичную ссылку!
        return f"{S3_PUBLIC}/{object_name}"
        
    except Exception as e:
        logging.error(f"Ошибка загрузки в S3: {e}")
        return None