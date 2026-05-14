from .utils import now_kst


DISCLAIMER = "※ 본 브리핑은 투자 추천이 아닌 뉴스/공시 정보 정리입니다."


def _format_news_item(index, item):
    source = item.get("source") or "출처 미상"
    title = item.get("title") or "제목 없음"
    published_at = item.get("published_at") or "날짜 미상"
    link = item.get("original_link") or item.get("link") or ""

    lines = ["%s. [%s] %s" % (index, source, title), "   날짜: %s" % published_at]
    if link:
        lines.append("   링크: %s" % link)
    return "\n".join(lines)


def _format_disclosure(index, item):
    corp_name = item.get("corp_name") or "회사명 미상"
    report_name = item.get("report_name") or "보고서명 미상"
    received_at = item.get("received_at") or "접수일 미상"
    link = item.get("link") or ""

    lines = ["%s. [%s] %s" % (index, corp_name, report_name), "   접수일: %s" % received_at]
    if link:
        lines.append("   링크: %s" % link)
    return "\n".join(lines)


def _format_short_news_item(index, item):
    source = item.get("source") or "출처 미상"
    title = item.get("title") or "제목 없음"
    link = item.get("original_link") or item.get("link") or ""

    lines = ["%s. [%s] %s" % (index, source, title)]
    if link:
        lines.append("   %s" % link)
    return "\n".join(lines)


def group_news_by_section(news_items):
    grouped = []
    section_map = {}
    for item in news_items:
        section = item.get("section") or "기타 뉴스"
        if section not in section_map:
            section_map[section] = []
            grouped.append((section, section_map[section]))
        section_map[section].append(item)
    return grouped


def _compact_summary(summary):
    if not summary:
        return ""

    lines = []
    for raw_line in summary.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("- ", "* ")):
            line = line[2:].strip()
        lines.append("- %s" % line)
        if len(lines) >= 6:
            break
    return "\n".join(lines)


def _topic_candidates(summary, news_items, limit=6):
    seed_keywords = [
        "AI 반도체",
        "반도체",
        "저PBR/밸류업",
        "AI 인프라",
        "클라우드/AI 보안",
        "바이오",
        "IT",
        "에너지",
        "로봇",
        "스마트홈",
        "카메라모듈",
        "CCL",
    ]
    haystack = " ".join(
        [summary or ""]
        + [item.get("title") or "" for item in news_items]
        + [item.get("description") or "" for item in news_items]
    )

    topics = []
    for keyword in seed_keywords:
        checks = keyword.replace("/", " ").split()
        if any(check and check in haystack for check in checks):
            topics.append(keyword)
        if len(topics) >= limit:
            break
    return topics


def _interest_lines(news_items, disclosures):
    lines = []
    for company in ["싸이토젠", "경인양행"]:
        news_count = sum(1 for item in news_items if company in (item.get("title") or ""))
        disclosure_count = sum(1 for item in disclosures if company in (item.get("corp_name") or ""))
        if disclosure_count:
            lines.append("- %s: DART 공시 %s건 확인" % (company, disclosure_count))
        elif news_count:
            lines.append("- %s: 관련 뉴스 %s건, 신규 관심 공시는 없음" % (company, news_count))
        else:
            lines.append("- %s: 특이 뉴스/공시 없음" % company)
    return lines


def format_compact_briefing(
    news_items,
    disclosures=None,
    generated_at=None,
    summary=None,
    links_per_section=2,
):
    generated_at = generated_at or now_kst()
    disclosures = disclosures or []
    links_per_section = max(1, int(links_per_section or 1))

    lines = [
        "Market Brief",
        generated_at.strftime("%Y-%m-%d %H:%M"),
        "",
    ]

    compact_summary = _compact_summary(summary)
    if compact_summary:
        lines.extend(["## 핵심 요약", compact_summary, ""])

    topics = _topic_candidates(summary, news_items)
    if topics:
        lines.append("## 오늘 볼 테마")
        lines.extend("- %s" % topic for topic in topics)
        lines.append("")

    interest_lines = _interest_lines(news_items, disclosures)
    if interest_lines:
        lines.append("## 관심 종목/공시")
        lines.extend(interest_lines)
        lines.append("")

    if news_items:
        lines.append("## 주요 기사")
        for section, items in group_news_by_section(news_items):
            lines.append("[%s]" % section)
            for index, item in enumerate(items[:links_per_section], start=1):
                lines.append(_format_short_news_item(index, item))
            lines.append("")
    else:
        lines.extend(["## 주요 기사", "수집된 뉴스가 없습니다.", ""])

    if disclosures:
        lines.append("## DART 공시")
        for index, item in enumerate(disclosures[:5], start=1):
            lines.append(_format_disclosure(index, item))
        lines.append("")

    lines.append(DISCLAIMER)
    return "\n".join(lines).strip()


def format_briefing(news_items, disclosures=None, generated_at=None, summary=None):
    generated_at = generated_at or now_kst()
    disclosures = disclosures or []

    lines = [
        "Market Brief",
        "생성 시각: %s" % generated_at.strftime("%Y-%m-%d %H:%M"),
        "",
    ]

    if summary:
        lines.append("## 오늘의 요약")
        lines.append(summary.strip())
        lines.append("")

    if news_items:
        for section, items in group_news_by_section(news_items):
            lines.append("## %s" % section)
            for index, item in enumerate(items, start=1):
                lines.append(_format_news_item(index, item))
            lines.append("")
    else:
        lines.extend(["## 뉴스", "수집된 뉴스가 없습니다.", ""])

    lines.append("## DART 공시")
    if disclosures:
        for index, item in enumerate(disclosures, start=1):
            lines.append(_format_disclosure(index, item))
    else:
        lines.append("수집된 관심 종목 공시가 없습니다.")

    lines.extend(["", DISCLAIMER])
    return "\n".join(lines).strip()


def split_message(message, max_length=3500):
    if len(message) <= max_length:
        return [message]

    chunks = []
    current = ""
    line_limit = max_length - 20

    for line in message.splitlines():
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
    return ["[%s/%s]\n%s" % (index, total, chunk) for index, chunk in enumerate(chunks, start=1)]
