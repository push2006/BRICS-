"""Email delivery. OFF unless ENABLE_EMAIL=true in .env.
Data-loss-safe: build_digest() never marks articles sent — only a
confirmed send does, via mark_sent() in app.py."""
import smtplib
import datetime
from email.mime.text import MIMEText
import config as C
from video import load_streams


def build_digest(articles):
    if not articles:
        return None, []
    by_cat = {}
    for a in articles:
        by_cat.setdefault(a.get("category", "GENERAL"), []).append(a)

    date_str = datetime.date.today().strftime("%d %b %Y")
    html = [f"<h2>🌍 BRICS Live Monitor — Digest {date_str}</h2>",
            f"<p>{len(articles)} items across {len(by_cat)} categories</p>"]

    for cat, items in by_cat.items():
        html.append(f"<h3>{cat}</h3><ul>")
        for a in items:
            corroborated = ""
            if a.get("corroborated_by") and len(a["corroborated_by"]) > 1:
                corroborated = f" <i>(confirmed by {len(a['corroborated_by'])} sources)</i>"
            html.append(f"<li><a href='{a['url']}'>{a['title']}</a> — {a['source']}, {a.get('country','')}{corroborated}</li>")
        html.append("</ul>")

    # Live stream links — email can't play video, so link to the watch page
    streams = load_streams()
    if streams:
        html.append("<h3>📺 Live Feeds (open in browser)</h3><ul>")
        for s in streams:
            html.append(f"<li><a href='{s['watch_url']}'>{s['name']}</a></li>")
        html.append("</ul>")

    ids = [a["id"] for a in articles if "id" in a]
    return "\n".join(html), ids


def send(html, subject=None):
    if not C.ENABLE_EMAIL or not html:
        return False
    subject = subject or f"🌍 BRICS Live Monitor — {datetime.date.today().strftime('%d %b %Y')}"
    msg = MIMEText(html, "html")
    msg["Subject"] = subject
    msg["From"] = C.EMAIL_FROM
    msg["To"] = C.EMAIL_TO

    # BUG FIX: previously `C.EMAIL_TO.split(",")` — an address list like
    # "a@x.com, b@x.com" (space after the comma, common when pasted) sent
    # " b@x.com" with a leading space as a literal recipient, which most
    # SMTP servers will reject or silently drop. Also drops any empty
    # entries from a trailing comma.
    recipients = [addr.strip() for addr in C.EMAIL_TO.split(",") if addr.strip()]

    with smtplib.SMTP(C.SMTP_HOST, C.SMTP_PORT) as server:
        server.starttls()
        server.login(C.EMAIL_FROM, C.EMAIL_APP_PASSWORD)
        server.sendmail(C.EMAIL_FROM, recipients, msg.as_string())
    return True
