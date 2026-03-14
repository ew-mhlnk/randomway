from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Разрешаем CORS чтобы Next.js мог делать запросы
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://randomway.pro"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {"status": "ok"}

# Сюда Next.js будет присылать данные из Mini App
@app.post("/auth")
async def verify_telegram_data(init_data: str):
    # Здесь будет логика проверки HMAC с помощью BOT_TOKEN
    pass