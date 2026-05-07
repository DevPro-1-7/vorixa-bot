"""
CharglyBot V3 — الإعدادات المركزية
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN:               str = os.getenv("BOT_TOKEN", "")
ADMIN_ID:                int = int(os.getenv("ADMIN_ID", "0"))
SUPPORT_LINK:            str = os.getenv("SUPPORT_LINK", "@Support")
PAYMENT_NUMBER:          str = os.getenv("PAYMENT_NUMBER", "0770000000")
PAYMENT_NAME:            str = os.getenv("PAYMENT_NAME", "محمد أحمد")
PAYMENT_TIMEOUT_MINUTES: int = int(os.getenv("PAYMENT_TIMEOUT_MINUTES", "15"))

# حماية السبام
RATE_LIMIT_SECONDS: int = 5
