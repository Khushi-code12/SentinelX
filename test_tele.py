import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# Import after loading .env so the module picks up the credentials
from telegram_alerts import send_alert, is_configured

if not is_configured():
    raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env first")

send_alert("🧪 Test alert from SentinelX")
