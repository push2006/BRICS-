"""Unified dashboard + cloud trigger routes.
Works in BOTH deploy modes:
  - DEPLOY_MODE=local  -> scheduler.py runs the 24/7 collect/report loop
                          in the background; run this file too (or use
                          `python run_all.py`) just to view the dashboard
                          at http://localhost:5000
  - DEPLOY_MODE=cloud  -> this is the single process Render runs; an
                          external scheduler hits /trigger-collect and
                          /trigger-report to drive the 24/7 loop
"""
import csv
import io
import datetime
from flask import Flask, request, jsonify, render_template, Response
import config as C
from app import cmd_collect, cmd_report
from database import get_store
from collectors.rss import load_sources, get_source_status
from video import load_streams, add_stream, remove_stream
from processing.classifier import is_critical, filter_brics

app = Flask(__name__)

CRITICAL_WINDOW = datetime.timedelta(hours=24)


def _auth_ok():
    return request.args.get("key") == C.TRIGGER_SECRET


def _dashboard_key_ok(req):
    """Checks the key from either the query string or a submitted form/JSON
    body, so the on-page 'add stream' form works without extra JS wiring."""
    key = req.args.get("key") or req.form.get("key")
    if key is None and req.is_json:
        key = (req.get_json(silent=True) or {}).get("key")
    return key == C.DASHBOARD_KEY


def _is_within_window(article, now, window):
    """Parses `collected_at` (an ISO 8601 string written by database.py) and
    returns True if it falls within `window` of `now`. Articles with a
    missing/unparseable timestamp are treated as NOT recent, rather than
    crashing the whole request — a single bad row shouldn't take down the
    dashboard."""
    raw = article.get("collected_at")
    if not raw:
        return False
    try:
        collected = datetime.datetime.fromisoformat(raw)
    except ValueError:
        return False
    return (now - collected) <= window


def _sources_with_status():
    """BUG FIX: the dashboard's "Sources in use" panel previously just
    echoed config/sources.yaml verbatim — every source looked identical
    whether it was returning 60 fresh articles or had been silently dead
    for weeks (CCTV, G1/Globo, Ahram Online, etc. — see collectors/rss.py).
    This merges in the last collection cycle's per-source result so that's
    finally visible on the page instead of only in the console."""
    sources = load_sources()
    status_map = get_source_status()
    for s in sources:
        st = status_map.get(s.get("name"))
        if st:
            s["last_status"] = st.get("status")
            s["last_count"] = st.get("count")
            s["last_message"] = st.get("message")
            s["last_checked"] = st.get("checked_at")
        else:
            # Never run yet this session, or a scrape/tier-3 source (which
            # doesn't go through rss.py's status tracking at all).
            s["last_status"] = None
    return sources


def _critical_recent(articles, now):
    """BUG FIX: previously `critical = [a for a in articles if is_critical(a)]`
    was labeled "Critical (24h)" on the dashboard but never actually checked
    the timestamp — it just kept-word-matched over whatever `store.recent()`
    happened to return, so week-old critical items would show up as if they
    were from the last day. This actually applies the 24h window."""
    return [a for a in articles if is_critical(a) and _is_within_window(a, now, CRITICAL_WINDOW)]


@app.get("/health")
def health():
    return jsonify({"status": "ok", "deploy_mode": C.DEPLOY_MODE, "storage": C.STORAGE_BACKEND})


@app.get("/")
@app.get("/dashboard")
def dashboard():
    store = get_store()
    articles = filter_brics(store.recent(300))  # safety filter for older/mixed data
    now = datetime.datetime.utcnow()
    critical = _critical_recent(articles, now)
    sources = _sources_with_status()
    streams = load_streams()
    return render_template(
        "dashboard.html",
        articles=articles,
        critical=critical,
        critical_count=len(critical),
        sources=sources,
        streams=streams,
        total=len(articles),
        refreshed=now.strftime("%d %b %Y, %H:%M UTC"),
    )


@app.get("/api/articles")
def api_articles():
    store = get_store()
    articles = filter_brics(store.recent(300))
    now = datetime.datetime.utcnow()
    critical = _critical_recent(articles, now)
    return jsonify({
        "articles": articles,
        "critical": critical,
        "total": len(articles),
        "critical_count": len(critical),
        "refreshed": now.strftime("%d %b %Y, %H:%M:%S UTC"),
    })


@app.get("/api/sources")
def api_sources():
    return jsonify(_sources_with_status())


@app.get("/api/streams")
def api_streams():
    return jsonify(load_streams())


@app.post("/api/streams")
def api_add_stream():
    if not _dashboard_key_ok(request):
        return jsonify({"error": "unauthorized — wrong dashboard key"}), 401
    payload = request.get_json(silent=True) or request.form
    try:
        stream = add_stream(
            name=payload.get("name", ""),
            country=payload.get("country", ""),
            link=payload.get("link") or payload.get("video_id", ""),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"status": "added", "stream": stream})


@app.delete("/api/streams/<path:name>")
def api_delete_stream(name):
    if not _dashboard_key_ok(request):
        return jsonify({"error": "unauthorized — wrong dashboard key"}), 401
    removed = remove_stream(name)
    if not removed:
        return jsonify({"error": f'No stream named "{name}"'}), 404
    return jsonify({"status": "removed", "name": name})


@app.get("/export.csv")
def export_csv():
    """BUG FIX: previously built the CSV by hand-concatenating strings and
    only quoted `title` — any comma in `source`, `published`, etc. silently
    shifted every column after it. Using the stdlib `csv` module quotes and
    escapes every field correctly, including embedded quotes/newlines."""
    store = get_store()
    rows = store.recent(1000)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["title", "url", "source", "country", "category", "published", "collected_at"])
    for r in rows:
        writer.writerow([
            r.get("title", ""), r.get("url", ""), r.get("source", ""),
            r.get("country", ""), r.get("category", ""), r.get("published", ""),
            r.get("collected_at", ""),
        ])
    return Response(buf.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment;filename=brics_articles.csv"})


@app.post("/trigger-collect")
def trigger_collect():
    if not _auth_ok():
        return jsonify({"error": "unauthorized"}), 401
    new_items = cmd_collect()
    return jsonify({"new_items": len(new_items)})


@app.post("/trigger-report")
def trigger_report():
    if not _auth_ok():
        return jsonify({"error": "unauthorized"}), 401
    cmd_report()
    return jsonify({"status": "report cycle complete"})


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))