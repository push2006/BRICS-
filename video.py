"""Loads config/streams.yaml and builds YouTube embed URLs.

Accepts video_id as either a bare ID or a full YouTube URL in any common
format (watch?v=, youtu.be/, /live/, /embed/) — just paste the link."""
import re
import threading
import yaml

STREAMS_FILE = "config/streams.yaml"

# BUG FIX: add_stream()/remove_stream() do a read-modify-write on this file.
# run_all.py runs the scheduler (background thread) and the Flask dashboard
# (main thread) in the SAME process, so two requests/cycles touching streams
# at once could race and one write could clobber the other. This lock
# serializes those read-modify-write sections. It does not protect against
# a second, separate OS process also writing the file (out of scope here).
_STREAMS_LOCK = threading.Lock()

_URL_PATTERNS = [
    r"(?:youtube\.com/watch\?v=|youtube\.com/live/|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{6,})",
]


def extract_video_id(value):
    """Turn a pasted YouTube link (any common format) OR a bare video ID
    into just the video ID."""
    value = (value or "").strip()
    if not value:
        return ""
    for pattern in _URL_PATTERNS:
        m = re.search(pattern, value)
        if m:
            return m.group(1)
    # not a recognizable URL — assume it's already a bare ID
    return value


def _read_raw_streams():
    """Load the raw stream list from disk (no embed_url/watch_url injected —
    those are derived fields, not stored)."""
    with open(STREAMS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("streams", []) or []


def load_streams():
    streams = _read_raw_streams()
    for s in streams:
        # BUG FIX: previously `s["type"]` — a hand-edited or malformed entry
        # missing the "type" key raised KeyError and took down /dashboard,
        # /api/streams, AND the email digest (which also calls this) all at
        # once. `.get()` skips the entry instead of crashing the request.
        stype = s.get("type")
        if stype == "channel":
            channel_id = s.get("channel_id", "")
            if not channel_id:
                continue
            s["embed_url"] = f"https://www.youtube.com/embed/live_stream?channel={channel_id}"
            s["watch_url"] = f"https://www.youtube.com/channel/{channel_id}/live"
        elif stype == "video":
            vid = extract_video_id(s.get("video_id", ""))
            s["video_id"] = vid  # normalize in case a full URL was pasted
            s["embed_url"] = f"https://www.youtube.com/embed/{vid}"
            s["watch_url"] = f"https://www.youtube.com/watch?v={vid}"
        # else: unrecognized/missing type — leave it out of embed rendering
        # rather than crash; it'll just show without a playable embed.
    return streams


_FILE_HEADER = """# Live video streams to embed on the dashboard.
#
# Streams can be added/removed from the dashboard itself (no code editing
# needed) — this file is just where they're persisted. Editing by hand
# still works too; paste any YouTube link format into video_id.
"""


def _write_raw_streams(streams):
    """Persist the raw stream list back to config/streams.yaml."""
    with open(STREAMS_FILE, "w", encoding="utf-8") as f:
        f.write(_FILE_HEADER)
        f.write("\n")
        yaml.safe_dump({"streams": streams}, f, sort_keys=False, allow_unicode=True)


def add_stream(name, country, link):
    """Add a new video stream from a pasted YouTube link (or bare ID).
    Returns the normalized stream dict that was added."""
    name = (name or "").strip()
    country = (country or "Custom").strip() or "Custom"
    vid = extract_video_id(link)
    if not name:
        raise ValueError("Stream name is required.")
    if not vid:
        raise ValueError("Could not read a video ID from that link.")

    with _STREAMS_LOCK:
        streams = _read_raw_streams()
        if any(s.get("name", "").strip().lower() == name.lower() for s in streams):
            raise ValueError(f"A stream named \"{name}\" already exists.")

        new_stream = {"name": name, "country": country, "type": "video", "video_id": vid}
        streams.append(new_stream)
        _write_raw_streams(streams)
    return new_stream


def remove_stream(name):
    """Remove a stream by exact name. Returns True if something was removed."""
    name = (name or "").strip().lower()
    with _STREAMS_LOCK:
        streams = _read_raw_streams()
        kept = [s for s in streams if s.get("name", "").strip().lower() != name]
        if len(kept) == len(streams):
            return False
        _write_raw_streams(kept)
    return True
