import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

_raw_users = os.getenv("ALLOWED_TELEGRAM_USERS", "").strip()
ALLOWED_TELEGRAM_USERS = {
    int(x.strip()) for x in _raw_users.split(",") if x.strip().isdigit()
}

DB_PATH = os.getenv("DB_PATH", "gestion.db")

DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin").strip()
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
DASHBOARD_PASSWORD_HASH = os.getenv("DASHBOARD_PASSWORD_HASH", "").strip()
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").strip().lower() in {
    "1", "true", "yes", "on"
}
