from src.news_filter import filter_news_items


def test_filter_removes_political_bio_noise():
    result = filter_news_items(
        [
            {
                "section": "바이오 관련 뉴스",
                "title": '김영환 "후보와 무제한 맞짱토론 하자"',
                "description": "지방선거 후보 공방",
            },
            {
                "section": "바이오 관련 뉴스",
                "title": "HLB제약, 전립선암 치료제 허가 획득",
                "description": "바이오 제약 항암제 시장 확대",
            },
        ]
    )

    assert len(result["kept"]) == 1
    assert result["kept"][0]["title"].startswith("HLB제약")
    assert result["removed_by_section"]["바이오 관련 뉴스"] == 1


def test_filter_removes_us_section_without_us_market_context():
    result = filter_news_items(
        [
            {
                "section": "미국 증시 주요 뉴스",
                "title": "한국 배달앱인데 결국 다 미국기업?",
                "description": "우버 배민 인수설에 시장과 소비자 관심",
            },
            {
                "section": "미국 증시 주요 뉴스",
                "title": "뉴욕증시, 엔비디아 강세에 나스닥 상승",
                "description": "미국 증시에서 기술주 주가가 강세",
            },
        ]
    )

    assert len(result["kept"]) == 1
    assert "뉴욕증시" in result["kept"][0]["title"]
    assert result["removed_by_section"]["미국 증시 주요 뉴스"] == 1


def test_filter_watchlist_requires_company_name():
    result = filter_news_items(
        [
            {
                "section": "싸이토젠 뉴스",
                "title": "골든크로스 종목",
                "description": "인바디 동방선기 관련 내용",
            },
            {
                "section": "싸이토젠 뉴스",
                "title": "싸이토젠, 신규 사업 기대감",
                "description": "싸이토젠 주가 관련 뉴스",
            },
        ]
    )

    assert len(result["kept"]) == 1
    assert result["kept"][0]["title"].startswith("싸이토젠")


def test_filter_keeps_it_industry_news():
    result = filter_news_items(
        [
            {
                "section": "IT 관련 뉴스",
                "title": "클라우드 9조 시장, AI 인프라 경쟁 확대",
                "description": "소프트웨어와 데이터센터 투자 확대",
            }
        ]
    )

    assert len(result["kept"]) == 1
