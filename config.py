"""Central config: every feature is read from .env, everything defaults OFF/local."""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool(key, default="false"):
    return os.getenv(key, default).strip().lower() in ("1", "true", "yes", "on")


def _list(key, default=""):
    raw = os.getenv(key, default)
    return [x.strip() for x in raw.split(",") if x.strip()]


# ---- Deploy / storage ----
DEPLOY_MODE = os.getenv("DEPLOY_MODE", "local")          # local | cloud
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "sqlite")  # sqlite | mongodb
SQLITE_PATH = os.getenv("SQLITE_PATH", "data/newsbot.db")
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "newsbot")

# ---- Delivery channels ----
ENABLE_EMAIL = _bool("ENABLE_EMAIL")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

ENABLE_WHATSAPP = _bool("ENABLE_WHATSAPP")
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "")
WHATSAPP_APIKEY = os.getenv("WHATSAPP_APIKEY", "")

ENABLE_TELEGRAM = _bool("ENABLE_TELEGRAM")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ---- Schedule ----
# Tier 1 (wire agencies: TASS, RIA, Xinhua, IRNA) actually publish fast —
# worth polling often. Tier 2 (regular outlets) rarely refresh faster than
# this anyway, so polling them as often as tier 1 just burns requests/quota
# on sources that haven't changed. Kept separate so each can be tuned in
# .env without touching code.
COLLECT_INTERVAL_TIER1_MINUTES = int(os.getenv("COLLECT_INTERVAL_TIER1_MINUTES", "10"))
COLLECT_INTERVAL_TIER2_MINUTES = int(os.getenv("COLLECT_INTERVAL_TIER2_MINUTES", "30"))
DIGEST_TIMES = _list("DIGEST_TIMES", "09:00,20:00")

# ---- Cloud trigger security ----
TRIGGER_SECRET = os.getenv("TRIGGER_SECRET", "changeme")

# ---- Optional features ----
ENABLE_CRITICAL_ALERTS = _bool("ENABLE_CRITICAL_ALERTS")
CRITICAL_KEYWORDS = _list("CRITICAL_KEYWORDS", "attack,explosion,resign,coup,ceasefire,sanctions")

ENABLE_WEEKLY_REPORT = _bool("ENABLE_WEEKLY_REPORT")
WEEKLY_REPORT_DAY = os.getenv("WEEKLY_REPORT_DAY", "Monday")

ENABLE_DASHBOARD = _bool("ENABLE_DASHBOARD")
DASHBOARD_KEY = os.getenv("DASHBOARD_KEY", "changeme")

ENABLE_TIER3_SCRAPE = _bool("ENABLE_TIER3_SCRAPE")

DEDUPE_THRESHOLD = float(os.getenv("DEDUPE_THRESHOLD", "0.8"))
ACTIVE_CATEGORIES = _list("ACTIVE_CATEGORIES", "GEOPOLITICS,TRADE,SANCTIONS,RISK,CONFERENCE,GENERAL")

SOURCES_FILE = os.getenv("SOURCES_FILE", "config/sources.yaml")