#!/usr/bin/env bash
# One-off run, e.g. via cron: 0 9,20 * * * /path/to/run_daily.sh
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null
python app.py run
