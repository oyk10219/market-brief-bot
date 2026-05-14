from collections import defaultdict


GENERAL_MARKET_TERMS = [
    "주가",
    "증시",
    "주식",
    "코스피",
    "코스닥",
    "나스닥",
    "다우",
    "s&p",
    "s&p500",
    "뉴욕증시",
    "투자",
    "순매수",
    "순매도",
    "외국인",
    "기관",
    "개인",
    "etf",
    "테마",
    "시총",
    "상장",
    "실적",
    "영업익",
    "매출",
    "수주",
    "공급망",
    "공시",
    "유상증자",
    "전환사채",
    "자사주",
    "배당",
    "인수",
    "합병",
]

EXCLUDE_TERMS = [
    "지방선거",
    "대선",
    "총선",
    "후보",
    "정당",
    "국회의원",
    "무제한 맞짱토론",
    "연예",
    "예능",
    "드라마",
    "영화",
    "스포츠",
    "야구",
    "축구",
    "농구",
    "맛집",
    "여행",
    "날씨",
]

SECTION_RULES = {
    "한국 증시 주요 뉴스": [
        "한국 증시",
        "국내 증시",
        "코스피",
        "코스닥",
        "외국인",
        "기관",
        "개인 순매수",
        "개인 순매도",
        "증권",
    ],
    "미국 증시 주요 뉴스": [
        "미국 증시",
        "미 증시",
        "美 증시",
        "뉴욕증시",
        "나스닥",
        "s&p",
        "다우",
        "월가",
        "연준",
        "fomc",
        "미 국채",
        "미국채",
        "엔비디아",
        "테슬라",
        "애플",
        "마이크로소프트",
        "아마존",
        "메타",
        "알파벳",
        "구글",
        "브로드컴",
        "amd",
        "인텔",
    ],
    "IT 관련 뉴스": [
        "it",
        "ai",
        "인공지능",
        "클라우드",
        "보안",
        "소프트웨어",
        "데이터센터",
        "반도체",
        "서버",
        "네트워크",
        "플랫폼",
        "디지털",
    ],
    "오늘 강한 테마 후보": [
        "주가",
        "테마",
        "급등",
        "강세",
        "상승",
        "매수",
        "수급",
        "관련주",
        "수혜",
        "부각",
    ],
    "반도체 관련 뉴스": [
        "반도체",
        "hbm",
        "메모리",
        "파운드리",
        "패키징",
        "웨이퍼",
        "소부장",
        "장비",
        "소재",
        "삼성전자",
        "sk하이닉스",
        "엔비디아",
        "tsmc",
    ],
    "바이오 관련 뉴스": [
        "바이오",
        "제약",
        "임상",
        "fda",
        "치료제",
        "신약",
        "의료기기",
        "헬스케어",
        "항암",
        "진단",
    ],
}

US_TITLE_TERMS = [
    "미국 증시",
    "미 증시",
    "美 증시",
    "뉴욕증시",
    "나스닥",
    "s&p",
    "다우",
    "월가",
    "연준",
    "fomc",
    "美",
    "엔비디아",
    "테슬라",
    "애플",
    "마이크로소프트",
    "아마존",
    "메타",
    "알파벳",
    "구글",
    "브로드컴",
    "amd",
    "인텔",
]


def _text(item):
    return " ".join(
        [
            item.get("title") or "",
            item.get("description") or "",
            item.get("article_text") or "",
        ]
    ).lower()


def _title_text(item):
    return (item.get("title") or "").lower()


def _contains_any(text, keywords):
    return any(keyword.lower() in text for keyword in keywords)


def _watchlist_company(section):
    if section.endswith(" 뉴스") and section not in SECTION_RULES:
        return section[:-3].strip()
    return ""


def _is_relevant(item):
    section = item.get("section") or ""
    text = _text(item)

    company = _watchlist_company(section)
    if company:
        return company.lower() in text

    section_terms = SECTION_RULES.get(section)
    if section == "미국 증시 주요 뉴스" and not _contains_any(_title_text(item), US_TITLE_TERMS):
        return False

    if section_terms and not _contains_any(text, section_terms):
        return False

    has_market_context = _contains_any(text, GENERAL_MARKET_TERMS)
    has_section_context = _contains_any(text, section_terms or [])

    if _contains_any(text, EXCLUDE_TERMS) and not (has_market_context and has_section_context):
        return False

    if section_terms:
        return has_section_context and (
            has_market_context or section in ("IT 관련 뉴스", "반도체 관련 뉴스", "바이오 관련 뉴스")
        )

    return has_market_context


def filter_news_items(items):
    kept = []
    removed = []
    removed_by_section = defaultdict(int)

    for item in items:
        if _is_relevant(item):
            kept.append(item)
            continue

        removed.append(item)
        removed_by_section[item.get("section") or "기타 뉴스"] += 1

    return {
        "kept": kept,
        "removed": removed,
        "removed_by_section": dict(removed_by_section),
    }
