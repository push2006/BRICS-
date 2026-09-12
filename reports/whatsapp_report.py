"""WhatsApp delivery via CallMeBot free API. OFF unless ENABLE_WHATSAPP=true.
Setup: message +34 644 71 79 92 on WhatsApp: 'I allow callmebot to send me
messages', then use the apikey it replies with."""
import requests
import config as C


def send(articles, limit=10):
    if not C.ENABLE_WHATSAPP or not articles:
        return False
    lines = [f"🌍 NewsBot: {len(articles)} new items"]
    for a in articles[:limit]:
        lines.append(f"- {a['title']} ({a['source']})")
    text = "\n".join(lines)
    resp = requests.get(
        "https://api.callmebot.com/whatsapp.php",
        params={"phone": C.WHATSAPP_PHONE, "text": text, "apikey": C.WHATSAPP_APIKEY},
        timeout=15,
    )
    return resp.status_code == 200
