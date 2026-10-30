import os
import asyncio
import traceback
from telegram import Bot

# Credentials come from the environment (or a .env file loaded by app.py).
# Never hardcode the bot token in source.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')


def is_configured():
    return bool(TELEGRAM_BOT_TOKEN and CHAT_ID)


async def send_telegram_message(text):
    try:
        # A fresh Bot per call: its HTTP client is bound to the event loop it
        # was opened on, and every alert runs in its own asyncio.run() loop.
        async with Bot(token=TELEGRAM_BOT_TOKEN) as bot:
            await bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception:
        print("[ERROR] Telegram send_message failed:", traceback.format_exc())


async def send_telegram_photo(path):
    try:
        async with Bot(token=TELEGRAM_BOT_TOKEN) as bot:
            with open(path, "rb") as f:
                await bot.send_photo(chat_id=CHAT_ID, photo=f)
    except Exception:
        print("[ERROR] Telegram send_photo failed:", traceback.format_exc())


async def _send_alert(text, photo_path):
    await send_telegram_message(text)
    if photo_path:
        await send_telegram_photo(photo_path)


def send_alert(text, photo_path=None):
    """Blocking helper: send a text alert (and optional photo). Safe to call from any thread."""
    if not is_configured():
        print("[WARN] Telegram not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID); skipping alert")
        return
    asyncio.run(_send_alert(text, photo_path))
