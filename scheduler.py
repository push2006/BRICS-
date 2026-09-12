"""Local 24/7 runner — use when DEPLOY_MODE=local.
Run: python scheduler.py   (keep the terminal / a screen session open,
or wrap it in a systemd service / Windows Task Scheduler for true 24/7).
Then separately run `python web.py` to view the dashboard at
http://localhost:5000 — or use run_all.py to start both together.
"""
import time
import logging
import os
import schedule
import config as C
from app import cmd_collect, cmd_report

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/app.log", level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def job_collect_tier1():
    """Wire agencies (TASS, RIA, Xinhua, IRNA) — polled often since they
    actually publish fast. Official/scrape sources skipped here; they run
    on the slower tier-2 job instead."""
    logging.info("running collect (tier 1)")
    try:
        cmd_collect(tiers=(1,), include_official=False)
    except Exception as e:
        logging.exception(f"tier-1 collect failed: {e}")


def job_collect_tier2():
    """Regular outlets + official/scrape sources — these don't refresh
    fast enough to justify the tier-1 interval."""
    logging.info("running collect (tier 2)")
    try:
        cmd_collect(tiers=(2,), include_official=True)
    except Exception as e:
        logging.exception(f"tier-2 collect failed: {e}")


def job_report():
    logging.info("running report")
    try:
        cmd_report()
    except Exception as e:
        logging.exception(f"report failed: {e}")


if __name__ == "__main__":
    print(f"[scheduler] tier 1 every {C.COLLECT_INTERVAL_TIER1_MINUTES} min, "
          f"tier 2 every {C.COLLECT_INTERVAL_TIER2_MINUTES} min; "
          f"digests at {', '.join(C.DIGEST_TIMES)}")
    schedule.every(C.COLLECT_INTERVAL_TIER1_MINUTES).minutes.do(job_collect_tier1)
    schedule.every(C.COLLECT_INTERVAL_TIER2_MINUTES).minutes.do(job_collect_tier2)
    for t in C.DIGEST_TIMES:
        schedule.every().day.at(t).do(job_report)

    job_collect_tier1()  # run both once immediately on startup
    job_collect_tier2()
    while True:
        schedule.run_pending()
        time.sleep(30)