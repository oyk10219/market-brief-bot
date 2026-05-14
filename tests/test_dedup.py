from src.utils import deduplicate_news


def test_deduplicate_news_by_title():
    items = [
        {"title": "반도체 뉴스", "link": "https://example.com/a"},
        {"title": "반도체 뉴스", "link": "https://example.com/b"},
    ]

    result = deduplicate_news(items)

    assert len(result) == 1
    assert result[0]["link"] == "https://example.com/a"


def test_deduplicate_news_by_link():
    items = [
        {"title": "첫 번째 제목", "link": "https://example.com/a"},
        {"title": "두 번째 제목", "link": "https://example.com/a/"},
    ]

    result = deduplicate_news(items)

    assert len(result) == 1
    assert result[0]["title"] == "첫 번째 제목"
