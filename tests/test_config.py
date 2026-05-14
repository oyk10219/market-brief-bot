import os

from src.config import load_config


def test_load_config_splits_single_chat_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111,222")
    monkeypatch.delenv("TELEGRAM_CHAT_IDS", raising=False)

    config = load_config()

    assert config.telegram_chat_ids == ["111", "222"]


def test_load_config_prefers_chat_ids(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "222,333,222")

    config = load_config()

    assert config.telegram_chat_ids == ["222", "333"]
