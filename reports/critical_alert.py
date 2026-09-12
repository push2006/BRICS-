"""Instant alert for critical items, bypassing the normal digest schedule.
OFF unless ENABLE_CRITICAL_ALERTS=true."""
import config as C
from processing.classifier import is_critical
from reports import email_report, whatsapp_report, telegram_report


def check_and_alert(articles):
    if not C.ENABLE_CRITICAL_ALERTS:
        return []
    critical = [a for a in articles if is_critical(a)]
    if not critical:
        return []

    lines = ["<h2>🚨 CRITICAL ALERT</h2><ul>"]
    for a in critical:
        lines.append(f"<li><a href='{a['url']}'>{a['title']}</a> — {a['source']}</li>")
    lines.append("</ul>")
    html = "\n".join(lines)

    if C.ENABLE_EMAIL:
        email_report.send(html, subject="🚨 NewsBot CRITICAL ALERT")
    if C.ENABLE_WHATSAPP:
        whatsapp_report.send(critical, limit=5)
    if C.ENABLE_TELEGRAM:
        telegram_report.send(critical, limit=5)

    return critical
