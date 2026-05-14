import json

from src import kakao_sender as kakao_module
from src.kakao_sender import KakaoSender


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_kakao_sender_refreshes_and_sends(monkeypatch):
    calls = []

    def fake_post(url, headers=None, data=None, timeout=None):
        calls.append((url, headers or {}, data or {}))
        if url == KakaoSender.TOKEN_URL:
            return FakeResponse(payload={"access_token": "access-token"})
        return FakeResponse(payload={"result_code": 0})

    monkeypatch.setattr(kakao_module.requests, "post", fake_post)

    sender = KakaoSender("rest-key", "refresh-token", max_text_length=200)
    result = sender.send_message("Market Brief")

    assert result == [{"result_code": 0}]
    assert calls[0][0] == KakaoSender.TOKEN_URL
    assert calls[0][2]["grant_type"] == "refresh_token"
    assert calls[1][0] == KakaoSender.SEND_ME_URL
    template = json.loads(calls[1][2]["template_object"])
    assert template["object_type"] == "text"
    assert template["text"] == "Market Brief"


def test_kakao_sender_splits_messages_within_limit():
    sender = KakaoSender("rest-key", "refresh-token", max_text_length=80)

    chunks = sender.split_message("가" * 200)

    assert len(chunks) > 1
    assert all(len(chunk) <= 80 for chunk in chunks)
