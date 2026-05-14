import hashlib
import html
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit


KST = timezone(timedelta(hours=9))
HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def now_kst():
    return datetime.now(KST)


def clean_html(value):
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = HTML_TAG_RE.sub("", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def normalize_title(title):
    return clean_html(title).lower()


def normalize_link(link):
    if not link:
        return ""
    parsed = urlsplit(str(link).strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def source_from_url(link):
    normalized = normalize_link(link)
    if not normalized:
        return "출처 미상"
    netloc = urlsplit(normalized).netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc or "출처 미상"


def parse_pub_date(value):
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(KST).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return clean_html(value)


def hash_text(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def mask_secret(value, visible=4):
    if not value:
        return ""
    text = str(value)
    if len(text) <= visible:
        return "*" * len(text)
    return text[:visible] + "*" * (len(text) - visible)


def deduplicate_news(items):
    seen_titles = set()
    seen_links = set()
    deduped = []

    for item in items:
        title_key = normalize_title(item.get("title", ""))
        link_key = normalize_link(item.get("link") or item.get("original_link", ""))

        if title_key and title_key in seen_titles:
            continue
        if link_key and link_key in seen_links:
            continue

        if title_key:
            seen_titles.add(title_key)
        if link_key:
            seen_links.add(link_key)
        deduped.append(item)

    return deduped
