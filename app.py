"""Core pipeline. Usage:
    python app.py init      # create local storage
    python app.py collect   # fetch + dedupe + classify + store
    python app.py report    # build & send digest for unsent articles
    python app.py run       # collect then report, once
"""
import sys
import config as C
import config_check
from database import get_store
from collectors import rss, official
from processing.dedupe import dedupe
from processing.classifier import classify_all, filter_brics
from reports import email_report, whatsapp_report, telegram_report, critical_alert


def cmd_init():
    get_store()
    print(f"[init] storage ready ({C.STORAGE_BACKEND})")


def cmd_collect(tiers=(1, 2), include_official=True):
    """tiers/include_official let the scheduler poll tier-1 wire agencies
    on a short interval and tier-2/official sources on a longer one,
    instead of hitting every source on one shared clock."""
    issues = config_check.check()
    hard = [i for i in issues if not i.startswith("[warning]")]
    if hard:
        print("[collect] blocked by config issues:")
        for i in hard:
            print(" -", i)
        return []

    store = get_store()
    raw = rss.fetch_all(tiers=tiers)
    if include_official:
        raw += official.fetch_all()
    print(f"[collect] fetched {len(raw)} raw items (tiers={tiers}, official={include_official})")
    deduped = dedupe(raw)
    classified = classify_all(deduped)
    brics_only = filter_brics(classified)
    print(f"[collect] {len(classified)} items after dedupe + category filter, "
          f"{len(brics_only)} are BRICS-relevant (dropped {len(classified)-len(brics_only)} off-topic)")

    new_items = store.insert_many(brics_only)
    print(f"[collect] {len(new_items)} new items stored")

    critical_alert.check_and_alert(new_items)
    return new_items


def cmd_report():
    store = get_store()
    unsent = store.unsent()
    if not unsent:
        print("[report] nothing new to send")
        return

    sent_any = False
    if C.ENABLE_EMAIL:
        html, ids = email_report.build_digest(unsent)
        if html and email_report.send(html):
            store.mark_sent(ids)
            sent_any = True
            print(f"[report] emailed {len(ids)} items")
    if C.ENABLE_WHATSAPP:
        if whatsapp_report.send(unsent):
            sent_any = True
            print("[report] sent WhatsApp summary")
    if C.ENABLE_TELEGRAM:
        if telegram_report.send(unsent):
            sent_any = True
            print("[report] sent Telegram summary")

    if not sent_any:
        print("[report] no delivery channel enabled/succeeded — "
              "items remain unsent in storage (see .env toggles)")


def cmd_run():
    cmd_collect()
    cmd_report()


COMMANDS = {"init": cmd_init, "collect": cmd_collect, "report": cmd_report, "run": cmd_run}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd not in COMMANDS:
        print(f"Unknown command '{cmd}'. Use one of: {', '.join(COMMANDS)}")
        sys.exit(1)
    COMMANDS[cmd]()