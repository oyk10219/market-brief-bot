import sqlite3

from src.database import BriefingDatabase


def test_database_disables_itself_when_sqlite_connect_fails(monkeypatch, tmp_path):
    def raise_disk_error(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(sqlite3, "connect", raise_disk_error)

    db = BriefingDatabase(tmp_path / "briefing.db")
    db.init_schema()

    assert db.disabled is True
    assert "disk I/O error" in db.error_message
    assert db.start_run() is None

    db.insert_news_items([{"title": "sample", "link": "https://example.com"}])
    db.record_sent_message(None, 1, "message", "DRY_RUN")
    db.record_error(None, "stage", "message")
    db.finish_run(None, "SUCCESS")
