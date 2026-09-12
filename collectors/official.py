"""Tier-3 sources (no reliable RSS). OFF by default — set
ENABLE_TIER3_SCRAPE=true only after checking each site's terms of use.

This is a stub, not a full scraper: it fetches the page and returns the
raw title so you have a starting point, rather than shipping brittle
per-site CSS selectors that will break the moment a site redesigns.
Add your own parsing rules per source as needed.
"""
import requests
import config as C
from collectors.rss import load_sources


def fetch_all():
    if not C.ENABLE_TIER3_SCRAPE:
        return []
    articles = []
    headers = {"User-Agent": "Mozilla/5.0 (NewsBotTemplate/1.0)"}
    for src in load_sources():
        if src.get("type") != "scrape" or src.get("tier") != 3:
            continue
        try:
            resp = requests.get(src["url"], headers=headers, timeout=15)
            resp.raise_for_status()
            articles.append({
                "title": f"[Check manually] {src['name']} homepage fetched OK",
                "url": src["url"],
                "source": src["name"],
                "country": src.get("country", ""),
                "summary": "Tier-3 stub fetch — add site-specific parsing in this file.",
                "published": "",
            })
        except Exception as e:
            print(f"[official] failed {src['name']}: {e}")
    return articles
