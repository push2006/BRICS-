"""Storage layer. Toggle STORAGE_BACKEND in .env — nothing else in the app
needs to know whether articles live in SQLite or MongoDB."""
import os
import sqlite3
import hashlib
import datetime
import config as C


def _hash(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


class SQLiteStore:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # timeout=30: how long a connection waits on a lock before raising
        # "database is locked", instead of the 5s default that this app's
        # concurrent dashboard reads + scheduler writes routinely exceeded.
        self.conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
        # WAL lets readers (dashboard) proceed while a write is in progress,
        # instead of the default journal mode where writers and readers
        # block each other — this is the main fix for "database is locked".
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT, url TEXT, source TEXT, country TEXT,
                category TEXT, summary TEXT, published TEXT,
                collected_at TEXT, emailed INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def insert(self, article):
        aid = _hash(article["url"])
        try:
            self.conn.execute(
                "INSERT INTO articles (id,title,url,source,country,category,summary,published,collected_at,emailed) "
                "VALUES (?,?,?,?,?,?,?,?,?,0)",
                (aid, article["title"], article["url"], article["source"], article.get("country", ""),
                 article.get("category", "GENERAL"), article.get("summary", ""),
                 article.get("published", ""), datetime.datetime.utcnow().isoformat()))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # already have it

    def insert_many(self, articles):
        """Same effect as calling insert() per article, but ONE commit for
        the whole batch instead of one per row. A collect cycle used to do
        68 separate write-transactions back to back — each one a window
        where the dashboard's read could hit "database is locked". This
        collapses it to a single lock window per cycle."""
        new_items = []
        cur = self.conn.cursor()
        for article in articles:
            aid = _hash(article["url"])
            cur.execute(
                "INSERT OR IGNORE INTO articles (id,title,url,source,country,category,summary,published,collected_at,emailed) "
                "VALUES (?,?,?,?,?,?,?,?,?,0)",
                (aid, article["title"], article["url"], article["source"], article.get("country", ""),
                 article.get("category", "GENERAL"), article.get("summary", ""),
                 article.get("published", ""), datetime.datetime.utcnow().isoformat()))
            if cur.rowcount == 1:
                new_items.append(article)
        self.conn.commit()
        return new_items

    def unsent(self):
        cur = self.conn.execute("SELECT * FROM articles WHERE emailed=0 ORDER BY collected_at DESC")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def mark_sent(self, ids):
        self.conn.executemany("UPDATE articles SET emailed=1 WHERE id=?", [(i,) for i in ids])
        self.conn.commit()

    def recent(self, limit=50):
        cur = self.conn.execute("SELECT * FROM articles ORDER BY collected_at DESC LIMIT ?", (limit,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


class MongoStore:
    def __init__(self, uri, dbname):
        from pymongo import MongoClient
        self.client = MongoClient(uri)
        self.col = self.client[dbname]["articles"]
        self.col.create_index("id", unique=True)

    def insert(self, article):
        aid = _hash(article["url"])
        doc = {**article, "id": aid, "emailed": False,
               "collected_at": datetime.datetime.utcnow().isoformat()}
        try:
            self.col.insert_one(doc)
            return True
        except Exception:
            return False  # duplicate key = already have it

    def unsent(self):
        return list(self.col.find({"emailed": False}).sort("collected_at", -1))

    def mark_sent(self, ids):
        self.col.update_many({"id": {"$in": ids}}, {"$set": {"emailed": True}})

    def insert_many(self, articles):
        """Mongo doesn't share SQLite's locking problem, but every store
        needs the same interface so app.py doesn't have to know which
        backend is active."""
        new_items = []
        for a in articles:
            if self.insert(a):
                new_items.append(a)
        return new_items

    def recent(self, limit=50):
        return list(self.col.find().sort("collected_at", -1).limit(limit))


_store_instance = None


def get_store():
    """Singleton: web.py and app.py each called this fresh per request/
    command, which meant every dashboard hit and every collect cycle
    opened its own separate SQLite connection to the same file — more
    simultaneous connections than necessary, and more chances to collide.
    One shared connection (safe here since it's opened with
    check_same_thread=False) plus WAL mode above is the real fix."""
    global _store_instance
    if _store_instance is None:
        if C.STORAGE_BACKEND == "mongodb":
            _store_instance = MongoStore(C.MONGODB_URI, C.MONGODB_DB)
        else:
            _store_instance = SQLiteStore(C.SQLITE_PATH)
    return _store_instance