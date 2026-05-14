from datetime import timedelta

import requests

from .utils import clean_html, now_kst


class DartFetcher:
    DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
    DART_VIEW_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=%s"

    def __init__(self, api_key, timeout=15):
        self.api_key = api_key
        self.timeout = timeout

    def fetch_recent_disclosures(self, target_companies=None, lookback_days=7, page_count=100):
        end_date = now_kst().date()
        begin_date = end_date - timedelta(days=max(1, int(lookback_days)))

        params = {
            "crtfc_key": self.api_key,
            "bgn_de": begin_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
            "page_no": 1,
            "page_count": max(1, min(int(page_count), 100)),
            "sort": "date",
            "sort_mth": "desc",
        }

        response = requests.get(self.DART_LIST_URL, params=params, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError("OpenDART API 오류: HTTP %s - %s" % (response.status_code, response.text[:500]))

        payload = response.json()
        status = payload.get("status")
        if status == "013":
            return []
        if status != "000":
            raise RuntimeError("OpenDART API 오류(%s): %s" % (status, payload.get("message", "")))

        companies = [name.strip() for name in (target_companies or []) if name.strip()]
        disclosures = []
        for raw in payload.get("list", []):
            corp_name = clean_html(raw.get("corp_name"))
            if companies and not any(company in corp_name for company in companies):
                continue

            rcept_no = clean_html(raw.get("rcept_no"))
            disclosures.append(
                {
                    "corp_name": corp_name,
                    "report_name": clean_html(raw.get("report_nm")),
                    "received_at": clean_html(raw.get("rcept_dt")),
                    "submitter": clean_html(raw.get("flr_nm")),
                    "stock_code": clean_html(raw.get("stock_code")),
                    "link": self.DART_VIEW_URL % rcept_no if rcept_no else "",
                }
            )
        return disclosures
