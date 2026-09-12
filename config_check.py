"""Run before collect/report: tells you exactly what's misconfigured."""
import sys
import config as C


def check():
    problems = []

    if C.STORAGE_BACKEND == "mongodb" and not C.MONGODB_URI:
        problems.append("STORAGE_BACKEND=mongodb but MONGODB_URI is empty.")
    if C.DEPLOY_MODE == "cloud" and C.STORAGE_BACKEND == "sqlite":
        problems.append("DEPLOY_MODE=cloud with STORAGE_BACKEND=sqlite — cloud hosts "
                         "usually wipe local disk on redeploy/restart. Use mongodb for cloud.")

    if C.ENABLE_EMAIL and not (C.EMAIL_FROM and C.EMAIL_TO and C.EMAIL_APP_PASSWORD):
        problems.append("ENABLE_EMAIL=true but EMAIL_FROM/EMAIL_TO/EMAIL_APP_PASSWORD incomplete.")
    if C.ENABLE_WHATSAPP and not (C.WHATSAPP_PHONE and C.WHATSAPP_APIKEY):
        problems.append("ENABLE_WHATSAPP=true but WHATSAPP_PHONE/WHATSAPP_APIKEY incomplete.")
    if C.ENABLE_TELEGRAM and not (C.TELEGRAM_BOT_TOKEN and C.TELEGRAM_CHAT_ID):
        problems.append("ENABLE_TELEGRAM=true but TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID incomplete.")

    if not (C.ENABLE_EMAIL or C.ENABLE_WHATSAPP or C.ENABLE_TELEGRAM):
        problems.append("[warning] No delivery channel enabled — the bot will collect "
                         "and store articles but never notify you. This is fine for a "
                         "dry run; check the dashboard or DB directly to see results.")

    if C.DEPLOY_MODE == "cloud" and C.TRIGGER_SECRET == "changeme":
        problems.append("TRIGGER_SECRET is still the default 'changeme' — set a real "
                         "secret before exposing web.py publicly.")

    return problems


if __name__ == "__main__":
    issues = check()
    if not issues:
        print("[config_check] All good — no issues found.")
        sys.exit(0)
    print("[config_check] Issues found:\n")
    for p in issues:
        print(" -", p)
    hard_fail = [p for p in issues if not p.startswith("[warning]")]
    sys.exit(1 if hard_fail else 0)
