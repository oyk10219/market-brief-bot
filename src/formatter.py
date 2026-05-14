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
