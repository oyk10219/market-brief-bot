from src.formatter import DISCLAIMER, format_briefing, format_compact_briefing, split_message


def test_format_briefing_contains_disclaimer():
    message = format_briefing(
        [
            {
                "section": "한국 증시 주요 뉴스",
                "title": "시장 뉴스",
                "source": "example.com",
                "published_at": "2026-05-14 08:00",
                "link": "https://example.com/news",
            }
        ],
        disclosures=[],
    )

    assert "Market Brief" in message
    assert "한국 증시 주요 뉴스" in message
    assert DISCLAIMER in message


def test_format_briefing_contains_summary():
    message = format_briefing([], disclosures=[], summary="- 테스트 요약")

    assert "## 오늘의 요약" in message
    assert "- 테스트 요약" in message


def test_format_compact_briefing_limits_links_per_section():
    message = format_compact_briefing(
        [
            {"section": "IT", "title": "첫 번째", "source": "a.com", "link": "https://a.com/1"},
            {"section": "IT", "title": "두 번째", "source": "a.com", "link": "https://a.com/2"},
            {"section": "IT", "title": "세 번째", "source": "a.com", "link": "https://a.com/3"},
        ],
        disclosures=[],
        summary="- 요약 하나\n- 요약 둘",
        links_per_section=2,
    )

    assert "## 핵심 요약" in message
    assert "## 주요 기사" in message
    assert "첫 번째" in message
    assert "두 번째" in message
    assert "세 번째" not in message
    assert DISCLAIMER in message


def test_split_message_keeps_limit():
    message = "\n".join(["긴 문장 %s" % index for index in range(100)])

    parts = split_message(message, max_length=120)

    assert len(parts) > 1
    assert all(len(part) <= 120 for part in parts)
