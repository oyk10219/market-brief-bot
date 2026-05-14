import requests

from .utils import clean_html, parse_pub_date, source_from_url


class NewsFetcher:
    NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self, client_id, client_secret, timeout=15):
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

    def fetch(self, query, display=5, sort="date"):
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        params = {
            "query": query,
            "display": max(1, min(int(display), 100)),
            "start": 1,
            "sort": sort,
        }

        response = requests.get(
            self.NAVER_NEWS_URL,
            headers=headers,
            params=params,
            timeout=self.timeout,
        )

        if response.status_code != 200:
            body = response.text[:500]
            raise RuntimeError("Naver Search API 오류: HTTP %s - %s" % (response.status_code, body))

        payload = response.json()
        items = []
        for raw in payload.get("items", []):
            link = raw.get("originallink") or raw.get("link") or ""
            items.append(
                {
                    "keyword": query,
                    "title": clean_html(raw.get("title")),
                    "description": clean_html(raw.get("description")),
                    "source": source_from_url(link),
                    "published_at": parse_pub_date(raw.get("pubDate")),
                    "link": raw.get("link") or "",
                    "original_link": raw.get("originallink") or "",
                }
            )
        return items
