import sqlite3
from datetime import datetime
from pathlib import Path

from .utils import hash_text


class BriefingDatabase:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.disabled = False
        self.error_message = ""

    def _disable(self, exc):
        self.disabled = True
        self.error_message = "%s: %s" % (exc.__class__.__name__, exc)

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        if self.disabled:
            return
        try:
            with self._connect() as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS briefing_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        started_at TEXT NOT NULL,
                        finished_at TEXT,
                        status TEXT NOT NULL,
                        item_count INTEGER DEFAULT 0,
                        message_count INTEGER DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS news_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        section TEXT,
                        keyword TEXT,
                        title TEXT NOT NULL,
                        source TEXT,
                        published_at TEXT,
                        link TEXT,
                        original_link TEXT,
                        description TEXT,
                        title_hash TEXT NOT NULL,
                        link_hash TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        UNIQUE(title_hash),
                        UNIQUE(link_hash)
                    );

                    CREATE TABLE IF NOT EXISTS sent_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id INTEGER,
                        message_part INTEGER,
                        text_hash TEXT NOT NULL,
                        telegram_message_id TEXT,
                        status TEXT NOT NULL,
                        sent_at TEXT NOT NULL,
                        FOREIGN KEY(run_id) REFERENCES briefing_runs(id)
                    );

                    CREATE TABLE IF NOT EXISTS errors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id INTEGER,
                        stage TEXT NOT NULL,
                        message TEXT NOT NULL,
                        traceback TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(run_id) REFERENCES briefing_runs(id)
                    );
                    """
                )
        except (sqlite3.Error, OSError) as exc:
            self._disable(exc)

    def start_run(self):
        if self.disabled:
            return None
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO briefing_runs (started_at, status) VALUES (?, ?)",
                    (datetime.utcnow().isoformat(timespec="seconds"), "RUNNING"),
                )
                return cursor.lastrowid
        except (sqlite3.Error, OSError) as exc:
            self._disable(exc)
            return None

    def finish_run(self, run_id, status, item_count=0, message_count=0):
        if self.disabled or not run_id:
            return
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE briefing_runs
                       SET finished_at = ?,
                           status = ?,
                           item_count = ?,
                           message_count = ?
                     WHERE id = ?
                    """,
                    (
                        datetime.utcnow().isoformat(timespec="seconds"),
                        status,
                        item_count,
                        message_count,
                        run_id,
                    ),
                )
        except (sqlite3.Error, OSError) as exc:
            self._disable(exc)

    def insert_news_items(self, items):
        if self.disabled:
            return
        try:
            with self._connect() as conn:
                for item in items:
                    title = item.get("title") or ""
                    link = item.get("link") or item.get("original_link") or title
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO news_items (
                            section, keyword, title, source, published_at, link,
                            original_link, description, title_hash, link_hash, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.get("section"),
                            item.get("keyword"),
                            title,
                            item.get("source"),
                            item.get("published_at"),
                            item.get("link"),
                            item.get("original_link"),
                            item.get("description"),
                            hash_text(title.strip().lower()),
                            hash_text(link.strip().lower()),
                            datetime.utcnow().isoformat(timespec="seconds"),
                        ),
                    )
        except (sqlite3.Error, OSError) as exc:
            self._disable(exc)

    def record_sent_message(self, run_id, message_part, text, status, telegram_message_id=None):
        if self.disabled:
            return
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO sent_messages (
                        run_id, message_part, text_hash, telegram_message_id, status, sent_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        message_part,
                        hash_text(text),
                        telegram_message_id,
                        status,
                        datetime.utcnow().isoformat(timespec="seconds"),
                    ),
                )
        except (sqlite3.Error, OSError) as exc:
            self._disable(exc)

    def record_error(self, run_id, stage, message, traceback_text=None):
        if self.disabled:
            return
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO errors (run_id, stage, message, traceback, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        stage,
                        str(message),
                        traceback_text,
                        datetime.utcnow().isoformat(timespec="seconds"),
                    ),
                )
        except (sqlite3.Error, OSError) as exc:
            self._disable(exc)
