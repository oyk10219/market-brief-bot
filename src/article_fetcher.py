import re

import requests
from bs4 import BeautifulSoup

from .formatter import group_news_by_section
from .utils import clean_html


SPACE_RE = re.compile(r"\s+")
SKIP_TEXT_RE = re.compile(
    r"(무단전재|재배포|저작권|copyright|기자|구독|로그인|회원가입|기사제보|"
    r"광고|관련기사|많이 본 뉴스|이 기사는|All rights reserved)",
    re.IGNORECASE,
)


class ArticleFetcher:
    def __init__(self, timeout=10, max_chars=2500):
        self.timeout = timeout
        self.max_chars = max_chars
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )

    def fetch_text(self, url):
        if not url:
            return ""

        response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
        content_type = response.headers.get("Content-Type", "")
        if response.status_code != 200:
            raise RuntimeError("기사 본문 요청 실패: HTTP %s" % response.status_code)
        if "html" not in content_type.lower() and "text" not in content_type.lower():
            raise RuntimeError("기사 본문이 HTML 형식이 아닙니다: %s" % content_type)

        response.encoding = response.apparent_encoding or response.encoding
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "noscript", "iframe", "svg", "form", "button"]):
            tag.decompose()

        container = self._best_container(soup)
        paragraphs = self._extract_paragraphs(container)
        text = "\n".join(paragraphs)
        text = SPACE_RE.sub(" ", text).strip()
        return text[: self.max_chars]

    def _best_container(self, soup):
        candidates = []
        selectors = [
            "article",
            "[itemprop='articleBody']",
            ".article_body",
            ".articleBody",
            ".article-view-content",
            ".article_view",
            ".newsct_article",
            "#dic_area",
            "#articeBody",
            "#articleBody",
            "#article_body",
            "#newsEndContents",
            "#article-view-content-div",
        ]

        for selector in selectors:
            candidates.extend(soup.select(selector))

        if not candidates:
            candidates = soup.find_all(["article", "section", "div", "main", "body"])

        best = soup.body or soup
        best_score = 0
        for candidate in candidates:
            text = candidate.get_text(" ", strip=True)
            score = len(text)
            if score > best_score:
                best = candidate
                best_score = score
        return best

    def _extract_paragraphs(self, container):
        paragraphs = []
        for tag in container.find_all(["p", "div"], recursive=True):
            text = clean_html(tag.get_text(" ", strip=True))
            text = SPACE_RE.sub(" ", text).strip()
            if len(text) < 40:
                continue
            if SKIP_TEXT_RE.search(text):
                continue
            if text in paragraphs:
                continue
            paragraphs.append(text)
            if sum(len(part) for part in paragraphs) >= self.max_chars:
                break

        if paragraphs:
            return paragraphs

        text = clean_html(container.get_text(" ", strip=True))
        text = SPACE_RE.sub(" ", text).strip()
        return [text[: self.max_chars]] if text else []


def enrich_news_with_articles(news_items, per_section=3, timeout=10, max_chars=2500, logger=None):
    fetcher = ArticleFetcher(timeout=timeout, max_chars=max_chars)
    enriched = 0
    failed = 0

    for section, items in group_news_by_section(news_items):
        count = 0
        for item in items:
            if count >= per_section:
                break
            url = item.get("original_link") or item.get("link")
            if not url:
                continue
            try:
                article_text = fetcher.fetch_text(url)
                if article_text:
                    item["article_text"] = article_text
                    item["article_fetched"] = True
                    enriched += 1
                    count += 1
                    if logger:
                        logger.debug("기사 본문 추출 성공 [%s]: %s", section, item.get("title"))
            except Exception as exc:
                failed += 1
                item["article_fetched"] = False
                item["article_error"] = str(exc)
                if logger:
                    logger.debug("기사 본문 추출 실패 [%s]: %s - %s", section, item.get("title"), exc)

    return {"enriched": enriched, "failed": failed}
