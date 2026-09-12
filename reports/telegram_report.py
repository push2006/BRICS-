"""Telegram delivery via official Bot API. OFF unless ENABLE_TELEGRAM=true.
Setup: message @BotFather -> /newbot -> copy token; add bot to your
channel/chat and get the chat id from https://api.telegram.org/bot<token>/getUpdates"""
import requests
import config as C


def send(articles, limit=10):
    if not C.ENABLE_TELEGRAM or not articles:
        return False
    lines = [f"🌍 *NewsBot*: {len(articles)} new items"]
    for a in articles[:limit]:
        lines.append(f"• [{a['title']}]({a['url']}) — {a['source']}")
    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{C.TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": C.TELEGRAM_CHAT_ID, "text": text,
        "parse_mode": "Markdown", "disable_web_page_preview": True,
    }, timeout=15)
    return resp.status_code == 200
