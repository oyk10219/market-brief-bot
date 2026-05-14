from datetime import datetime

from src.main import _admin_chat_id, _format_failure_alert


class DummyConfig:
    def __init__(self, admin_chat_id="", chat_ids=None):
        self.telegram_admin_chat_id = admin_chat_id
        self.telegram_chat_ids = chat_ids or []


def test_admin_chat_id_prefers_admin():
    config = DummyConfig(admin_chat_id="999", chat_ids=["111"])

    assert _admin_chat_id(config) == "999"


def test_admin_chat_id_falls_back_to_first_recipient():
    config = DummyConfig(chat_ids=["111", "222"])

    assert _admin_chat_id(config) == "111"


def test_format_failure_alert_contains_status_and_errors():
    message = _format_failure_alert(
        "PARTIAL_FAILED",
        datetime(2026, 5, 14, 8, 30),
        [{"stage": "dart", "message": "API 오류"}],
        run_id=7,
    )

    assert "MarketBriefBot 오류 알림" in message
    assert "상태: PARTIAL_FAILED" in message
    assert "실행 ID: 7" in message
    assert "- dart: API 오류" in message
