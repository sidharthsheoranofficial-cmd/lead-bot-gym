import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import Application, ApplicationBuilder

from bot import build_bot_app  # import the function from bot.py

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # your Render URL + "/webhook"

app = FastAPI()

# Build PTB application (this is your Telegram bot)
bot_app: Application = build_bot_app()


@app.on_event("startup")
async def set_webhook():
    await bot_app.initialize()
    """Automatically set webhook when the server starts."""
    await bot_app.bot.set_webhook(url=WEBHOOK_URL)
    print("Webhook set to:", WEBHOOK_URL)


@app.post("/webhook")
async def receive_update(request: Request):
    """Receive updates from Telegram via webhook."""
    data = await request.json()

    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)

    return JSONResponse({"status": "ok"})


@app.get("/health")
async def health():
    return {"status": "running"}
