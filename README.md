# BRICS Live Monitor

A fresh, standalone project — one unified dashboard combining live news,
embedded live video feeds, critical alerts, and the full source list, all
on a single page, plus a matching email digest. Not built on top of the
old Geo Intel Monitor codebase.

## What you get

- **One dashboard page** (`/dashboard`) — live video embeds at the top,
  a searchable/filterable news feed, a critical-alerts panel, and a live
  source list, all "at your fingertips" on one screen.
- **Live video** — embedded YouTube live streams for WION, CGTN, RT News,
  Al Jazeera English, France 24 (edit `config/streams.yaml` to add/remove
  any public YouTube channel — official summit broadcast can be added the
  same way once you have its channel ID).
- **Email digest** — same articles, grouped by category, plus a list of
  live-stream links (email can't play video, so it links out instead).
- **24/7**, either mode:
  - **Local**: `python run_all.py` — one command runs the collector loop
    and the dashboard together on your machine.
  - **Cloud**: deploy `web.py` to Render + MongoDB Atlas, driven by an
    external scheduler hitting `/trigger-collect` and `/trigger-report`.
- Everything else (storage, delivery channels, alerts) is togglable in
  `.env`, same pattern as before — all off except email/critical-alerts
  defaults, which you fill in with your own credentials.

## Quick start — local, everything visible immediately

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py init
python run_all.py
```

Open **http://localhost:5000** — the dashboard, live feeds, and article
list are all there immediately. The collector runs on startup and then
every `COLLECT_INTERVAL_MINUTES`.

To also get emails: edit `.env`, set `ENABLE_EMAIL=true` and fill in a
Gmail **App Password** (https://myaccount.google.com/apppasswords),
`EMAIL_FROM`, `EMAIL_TO`. Restart `run_all.py`.

## Cloud 24/7 (Render + MongoDB Atlas)

1. `.env`: `DEPLOY_MODE=cloud`, `STORAGE_BACKEND=mongodb`
2. MongoDB Atlas free tier → create cluster → database user → Network
   Access allow `0.0.0.0/0` → copy connection string into `MONGODB_URI`
3. Push this folder to GitHub, then on Render: New → Web Service →
   connect repo → build `pip install -r requirements.txt` → start command
   uses `Procfile` (`gunicorn web:app`) → add every `.env` variable in the
   Environment tab, including a real `TRIGGER_SECRET` (not `changeme`)
4. Confirm `https://your-app.onrender.com/health` returns ok, then visit
   `/dashboard` — live feeds and articles render the same as local
5. Set up an external scheduler (cron-job.org is free) to POST:
   - `/trigger-collect?key=YOUR_SECRET` every 15 min
   - `/trigger-report?key=YOUR_SECRET` at your digest times

## Adding/editing live feeds

Edit `config/streams.yaml` — each entry is a YouTube channel ID (or fixed
video ID). To add the official BRICS summit broadcast once you have its
channel, just add a new `channel` entry; no code changes needed.

## Adding/editing news sources

`config/sources.yaml` — same 33-source, 3-tier, 11-country BRICS list as
before, still fully editable YAML.

## Routes

| Route | Purpose |
|---|---|
| `GET /dashboard` (or `/`) | The unified live dashboard |
| `GET /export.csv` | Download all stored articles as CSV |
| `GET /api/articles` | JSON of recent articles |
| `GET /api/sources` | JSON of the current source list |
| `GET /health` | Uptime check |
| `POST /trigger-collect?key=SECRET` | Cloud mode: run one collect cycle |
| `POST /trigger-report?key=SECRET` | Cloud mode: run one report cycle |

## Notes

- Live embeds use YouTube's `live_stream?channel=` URL, which
  auto-switches to a channel's live broadcast if one is running, or shows
  their latest video otherwise — no API key needed, but verify channel
  IDs occasionally since they can change.
- Same data-loss-safe email logic as before: an article is only marked
  "sent" after a confirmed successful send.
