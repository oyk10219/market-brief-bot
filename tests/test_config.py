import os

from src.config import load_config


def test_load_config_splits_single_chat_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111,222")
    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "")

    config = load_config()

    assert config.telegram_chat_ids == ["111", "222"]


def test_load_config_prefers_chat_ids(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "222,333,222")

    config = load_config()

    assert config.telegram_chat_ids == ["222", "333"]


def test_load_config_reads_admin_chat_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "999")

    config = load_config()

    assert config.telegram_admin_chat_id == "999"


def test_load_config_reads_send_channels(monkeypatch):
    monkeypatch.setenv("SEND_CHANNELS", "telegram,kakao,telegram")

    config = load_config()

    assert config.send_channels == ["telegram", "kakao"]


def test_load_config_defaults_to_telegram_channel(monkeypatch):
    monkeypatch.setenv("SEND_CHANNELS", "")

    config = load_config()

    assert config.send_channels == ["telegram"]
