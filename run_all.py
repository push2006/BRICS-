"""Convenience launcher for LOCAL mode: runs the 24/7 collector loop in a
background thread AND serves the dashboard, both from one command.
    python run_all.py
Dashboard: http://localhost:5000
(For cloud mode, don't use this — deploy web.py alone; timing is driven
by the external scheduler hitting /trigger-collect and /trigger-report.)
"""
import threading
import config as C

if C.DEPLOY_MODE != "local":
    print(f"[run_all] DEPLOY_MODE={C.DEPLOY_MODE} — this launcher is for local "
          f"mode only. For cloud, deploy web.py and drive it with an external "
          f"scheduler (see README).")
    raise SystemExit(1)

from scheduler import job_collect_tier1, job_collect_tier2, job_report
import schedule
import time
import web


def scheduler_loop():
    schedule.every(C.COLLECT_INTERVAL_TIER1_MINUTES).minutes.do(job_collect_tier1)
    schedule.every(C.COLLECT_INTERVAL_TIER2_MINUTES).minutes.do(job_collect_tier2)
    for t in C.DIGEST_TIMES:
        schedule.every().day.at(t).do(job_report)
    job_collect_tier1()
    job_collect_tier2()
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()
    print("[run_all] scheduler running in background — dashboard at http://localhost:5000")
    import os
    web.app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))