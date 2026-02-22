import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = FastAPI()

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/set_webhook")
async def set_webhook():
    webhook_url = f"{BASE_URL}/api/webhook"
    await bot.set_webhook(webhook_url)
    return {"webhook_set_to": webhook_url}

@app.post("/api/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update(**data)
    await dp.feed_update(bot, update)
    return {"ok": True}