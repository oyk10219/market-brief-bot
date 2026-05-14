import requests


class TelegramSender:
    TELEGRAM_API_URL = "https://api.telegram.org/bot%s/sendMessage"

    def __init__(self, bot_token, chat_id, timeout=15):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout

    def send_message(self, text):
        url = self.TELEGRAM_API_URL % self.bot_token
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": False,
        }
        response = requests.post(url, data=payload, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError("Telegram Bot API 오류: HTTP %s - %s" % (response.status_code, response.text[:500]))

        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError("Telegram Bot API 오류: %s" % payload)
        return payload.get("result", {})

    def send_messages(self, messages):
        results = []
        for message in messages:
            results.append(self.send_message(message))
        return results
