import os
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests


AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
DEFAULT_REDIRECT_URI = "http://localhost:8765/kakao/callback"


def load_dotenv():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def token_request(data):
    response = requests.post(TOKEN_URL, data=data, timeout=15)
    if response.status_code != 200:
        raise RuntimeError("Kakao token API 오류: HTTP %s - %s" % (response.status_code, response.text[:500]))
    return response.json()


class CallbackHandler(BaseHTTPRequestHandler):
    auth_code = ""
    auth_error = ""

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        CallbackHandler.auth_code = (params.get("code") or [""])[0]
        CallbackHandler.auth_error = (params.get("error") or [""])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            (
                "<html><body>"
                "<h2>Market Brief Kakao 인증 완료</h2>"
                "<p>이 창은 닫아도 됩니다. 터미널을 확인해 주세요.</p>"
                "</body></html>"
            ).encode("utf-8")
        )

    def log_message(self, format, *args):
        return


def main():
    load_dotenv()

    rest_api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    redirect_uri = os.getenv("KAKAO_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()
    client_secret = os.getenv("KAKAO_CLIENT_SECRET", "").strip()

    if not rest_api_key:
        print("KAKAO_REST_API_KEY가 필요합니다. .env에 먼저 입력해 주세요.")
        return 2

    auth_params = {
        "response_type": "code",
        "client_id": rest_api_key,
        "redirect_uri": redirect_uri,
        "scope": "talk_message",
    }
    auth_url = "%s?%s" % (AUTH_URL, urlencode(auth_params))

    parsed_redirect = urlparse(redirect_uri)
    host = parsed_redirect.hostname or "localhost"
    port = parsed_redirect.port or 80

    print("아래 Redirect URI가 Kakao Developers에 등록되어 있어야 합니다.")
    print(redirect_uri)
    print("")
    print("카카오 로그인/동의 페이지를 엽니다.")
    print(auth_url)
    print("")

    server = HTTPServer((host, port), CallbackHandler)
    server.timeout = 1
    webbrowser.open(auth_url)

    started_at = time.time()
    while not CallbackHandler.auth_code and not CallbackHandler.auth_error:
        server.handle_request()
        if time.time() - started_at > 300:
            raise TimeoutError("5분 안에 인증 코드가 도착하지 않았습니다.")

    if CallbackHandler.auth_error:
        raise RuntimeError("Kakao OAuth 오류: %s" % CallbackHandler.auth_error)

    data = {
        "grant_type": "authorization_code",
        "client_id": rest_api_key,
        "redirect_uri": redirect_uri,
        "code": CallbackHandler.auth_code,
    }
    if client_secret:
        data["client_secret"] = client_secret

    payload = token_request(data)
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("refresh_token이 응답에 없습니다. Kakao Developers 설정을 확인해 주세요.")

    print("인증 성공입니다. 아래 값을 .env에 추가해 주세요.")
    print("")
    print("KAKAO_REFRESH_TOKEN=%s" % refresh_token)
    print("")
    print("토큰은 비밀번호처럼 취급해 주세요. GitHub나 채팅에 올리지 마세요.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("%s: %s" % (exc.__class__.__name__, exc))
        sys.exit(1)
