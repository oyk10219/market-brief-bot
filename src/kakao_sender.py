import json

import requests


class KakaoSender:
    TOKEN_URL = "https://kauth.kakao.com/oauth/token"
    SEND_ME_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

    def __init__(
        self,
        rest_api_key,
        refresh_token,
        client_secret="",
        link_url="https://github.com/oyk10219/market-brief-bot",
        timeout=15,
        max_text_length=200,
    ):
        self.rest_api_key = rest_api_key
        self.refresh_token = refresh_token
        self.client_secret = client_secret
        self.link_url = link_url
        self.timeout = timeout
        self.max_text_length = max(80, min(int(max_text_length or 200), 200))

    def refresh_access_token(self):
        data = {
            "grant_type": "refresh_token",
            "client_id": self.rest_api_key,
            "refresh_token": self.refresh_token,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = requests.post(self.TOKEN_URL, data=data, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError("Kakao token refresh 오류: HTTP %s - %s" % (response.status_code, response.text[:500]))

        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise RuntimeError("Kakao token refresh 오류: access_token이 없습니다.")
        return payload

    def _template_object(self, text):
        return {
            "object_type": "text",
            "text": text,
            "link": {
                "web_url": self.link_url,
                "mobile_web_url": self.link_url,
            },
            "button_title": "상세 보기",
        }

    def send_text(self, access_token, text):
        headers = {
            "Authorization": "Bearer %s" % access_token,
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        }
        data = {
            "template_object": json.dumps(self._template_object(text), ensure_ascii=False),
        }
        response = requests.post(self.SEND_ME_URL, headers=headers, data=data, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError("Kakao 나에게 보내기 오류: HTTP %s - %s" % (response.status_code, response.text[:500]))

        payload = response.json()
        if payload.get("result_code") != 0:
            raise RuntimeError("Kakao 나에게 보내기 오류: %s" % payload)
        return payload

    def split_message(self, message):
        text = str(message or "").strip()
        if not text:
            return []

        limit = self.max_text_length
        line_limit = max(1, limit - 20)
        chunks = []
        current = ""

        for line in text.splitlines():
            pending = line + "\n"
            if len(pending) > line_limit:
                if current:
                    chunks.append(current.rstrip())
                    current = ""
                for start in range(0, len(pending), line_limit):
                    chunks.append(pending[start:start + line_limit].rstrip())
                continue

            if len(current) + len(pending) > line_limit:
                chunks.append(current.rstrip())
                current = pending
            else:
                current += pending

        if current.strip():
            chunks.append(current.rstrip())

        total = len(chunks)
        if total <= 1:
            return chunks

        result = []
        for index, chunk in enumerate(chunks, start=1):
            prefix = "[%s/%s]\n" % (index, total)
            result.append(prefix + chunk)
        return result

    def send_message(self, message):
        token_payload = self.refresh_access_token()
        access_token = token_payload["access_token"]
        results = []
        for chunk in self.split_message(message):
            results.append(self.send_text(access_token, chunk))
        return results
