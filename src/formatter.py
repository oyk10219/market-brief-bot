from .utils import now_kst


DISCLAIMER = "※ 본 브리핑은 투자 추천이 아닌 뉴스/공시 정보 정리입니다."

IMPORTANT_DISCLOSURE_RULES = [
    (
        "주의",
        [
            "유상증자",
            "전환사채",
            "전환사채권",
            "신주인수권부사채",
            "최대주주변경",
            "거래정지",
            "주권매매거래정지",
            "불성실공시",
            "감사의견",
            "상장폐지",
            "관리종목",
            "횡령",
            "배임",
            "감자",
            "회생절차",
        ],
    ),
    (
        "체크",
        [
            "단일판매공급계약",
            "단일판매ㆍ공급계약",
            "단일판매·공급계약",
            "공급계약",
            "자기주식취득",
            "자기주식소각",
            "자기주식 취득",
            "자기주식 소각",
            "현금배당",
            "배당결정",
            "무상증자",
            "수주",
        ],
    ),
]


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


def _compact_text(value):
    text = str(value or "").lower()
    for token in (" ", "\t", "\n", "\r", "ㆍ", "·", "-", "_", "(", ")", "[", "]"):
        text = text.replace(token, "")
    return text


def classify_disclosure(item):
    report_name = item.get("report_name") or ""
    normalized_report = _compact_text(report_name)
    if not normalized_report:
        return None

    for label, keywords in IMPORTANT_DISCLOSURE_RULES:
        for keyword in keywords:
            if _compact_text(keyword) in normalized_report:
                return {
                    "label": label,
                    "keyword": keyword,
                    "corp_name": item.get("corp_name") or "회사명 미상",
                    "report_name": report_name,
                    "link": item.get("link") or "",
                }
    return None


def _important_disclosure_lines(disclosures, limit=5):
    alerts = []
    for item in disclosures or []:
        alert = classify_disclosure(item)
        if alert:
            alerts.append(alert)
        if len(alerts) >= limit:
            break

    lines = []
    for alert in alerts:
        line = "- [%s] %s: %s" % (alert["label"], alert["corp_name"], alert["report_name"])
        lines.append(line)
        if alert["link"]:
            lines.append("  %s" % alert["link"])
    return lines


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
    return "\n\n".join(lines)


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


def _item_contains_company(item, company):
    text = " ".join(
        [
            item.get("section") or "",
            item.get("title") or "",
            item.get("description") or "",
            item.get("corp_name") or "",
            item.get("report_name") or "",
        ]
    )
    return company in text


def _watchlist_lines(news_items, disclosures, watchlist_companies):
    if not watchlist_companies:
        return []

    lines = []
    for company in watchlist_companies:
        news_count = sum(1 for item in news_items if _item_contains_company(item, company))
        disclosure_count = sum(1 for item in disclosures if _item_contains_company(item, company))
        if news_count or disclosure_count:
            lines.append("- %s: 뉴스 %s건, 공시 %s건" % (company, news_count, disclosure_count))
        else:
            lines.append("- %s: 수집된 뉴스/공시 없음" % company)
    return lines


def format_compact_briefing(
    news_items,
    disclosures=None,
    generated_at=None,
    summary=None,
    links_per_section=1,
    watchlist_companies=None,
):
    generated_at = generated_at or now_kst()
    disclosures = disclosures or []
    watchlist_companies = watchlist_companies or []
    links_per_section = max(1, int(links_per_section or 1))

    lines = [
        "Market Brief",
        generated_at.strftime("%Y-%m-%d %H:%M"),
        "",
    ]

    important_disclosures = _important_disclosure_lines(disclosures)
    if important_disclosures:
        lines.extend(["## 중요 공시 체크"])
        lines.extend(important_disclosures)
        lines.append("")

    compact_summary = _compact_summary(summary)
    if compact_summary:
        lines.extend(["## 핵심 요약", compact_summary, ""])

    topics = _topic_candidates(summary, news_items)
    if topics:
        lines.append("## 오늘 볼 테마")
        lines.extend("- %s" % topic for topic in topics)
        lines.append("")

    watchlist = _watchlist_lines(news_items, disclosures, watchlist_companies)
    if watchlist:
        lines.append("## 관심 종목/공시")
        lines.extend(watchlist)
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

    lines.append("## DART 공시")
    if disclosures:
        for index, item in enumerate(disclosures[:links_per_section], start=1):
            lines.append(_format_disclosure(index, item))
    else:
        lines.append("최근 관심종목 공시는 없습니다.")
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

    important_disclosures = _important_disclosure_lines(disclosures)
    if important_disclosures:
        lines.extend(["## 중요 공시 체크"])
        lines.extend(important_disclosures)
        lines.append("")

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
        lines.append("수집된 공시가 없습니다.")

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
