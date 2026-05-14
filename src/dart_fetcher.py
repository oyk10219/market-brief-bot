import json
import zipfile
from io import BytesIO
from datetime import timedelta
from pathlib import Path
from xml.etree import ElementTree

import requests

from .utils import clean_html, now_kst


class DartFetcher:
    DART_CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
    DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
    DART_VIEW_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=%s"

    def __init__(self, api_key, timeout=15, corp_code_cache_path=None):
        self.api_key = api_key
        self.timeout = timeout
        self.corp_code_cache_path = Path(corp_code_cache_path) if corp_code_cache_path else None
        self._corp_codes = None

    def _load_corp_codes_from_cache(self):
        if not self.corp_code_cache_path or not self.corp_code_cache_path.exists():
            return []

        try:
            with self.corp_code_cache_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, ValueError):
            return []

        if isinstance(payload, list):
            return payload
        return []

    def _save_corp_codes_to_cache(self, corp_codes):
        if not self.corp_code_cache_path:
            return

        self.corp_code_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.corp_code_cache_path.open("w", encoding="utf-8") as file:
            json.dump(corp_codes, file, ensure_ascii=False)

    def _download_corp_codes(self):
        response = requests.get(
            self.DART_CORP_CODE_URL,
            params={"crtfc_key": self.api_key},
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise RuntimeError("OpenDART 회사코드 API 오류: HTTP %s" % response.status_code)

        try:
            archive = zipfile.ZipFile(BytesIO(response.content))
        except zipfile.BadZipFile:
            raise RuntimeError("OpenDART 회사코드 API 응답이 ZIP 형식이 아닙니다.")

        xml_name = archive.namelist()[0]
        root = ElementTree.fromstring(archive.read(xml_name))

        corp_codes = []
        for node in root.findall("list"):
            corp_codes.append(
                {
                    "corp_code": clean_html(node.findtext("corp_code")),
                    "corp_name": clean_html(node.findtext("corp_name")),
                    "stock_code": clean_html(node.findtext("stock_code")),
                    "modify_date": clean_html(node.findtext("modify_date")),
                }
            )
        return corp_codes

    def _load_corp_codes(self):
        if self._corp_codes is not None:
            return self._corp_codes

        cached = self._load_corp_codes_from_cache()
        if cached:
            self._corp_codes = cached
            return cached

        corp_codes = self._download_corp_codes()
        self._save_corp_codes_to_cache(corp_codes)
        self._corp_codes = corp_codes
        return corp_codes

    def _find_corp_code(self, company_name):
        corp_codes = self._load_corp_codes()
        exact_matches = [item for item in corp_codes if item.get("corp_name") == company_name]
        partial_matches = [item for item in corp_codes if company_name in (item.get("corp_name") or "")]
        matches = exact_matches or partial_matches
        if not matches:
            return ""

        listed_matches = [item for item in matches if item.get("stock_code")]
        selected = (listed_matches or matches)[0]
        return selected.get("corp_code") or ""

    def _fetch_list(self, begin_date, end_date, page_count=100, corp_code=None):
        params = {
            "crtfc_key": self.api_key,
            "bgn_de": begin_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
            "page_no": 1,
            "page_count": max(1, min(int(page_count), 100)),
            "sort": "date",
            "sort_mth": "desc",
        }
        if corp_code:
            params["corp_code"] = corp_code

        response = requests.get(self.DART_LIST_URL, params=params, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError("OpenDART API 오류: HTTP %s - %s" % (response.status_code, response.text[:500]))

        payload = response.json()
        status = payload.get("status")
        if status == "013":
            return []
        if status != "000":
            raise RuntimeError("OpenDART API 오류(%s): %s" % (status, payload.get("message", "")))

        return payload.get("list", [])

    def _normalize_disclosures(self, rows, companies=None):
        companies = [name.strip() for name in (companies or []) if name.strip()]
        disclosures = []
        for raw in rows:
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

    def _deduplicate_disclosures(self, disclosures):
        seen = set()
        result = []
        for item in disclosures:
            key = item.get("link") or "%s:%s:%s" % (
                item.get("corp_name"),
                item.get("report_name"),
                item.get("received_at"),
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def fetch_recent_disclosures(self, target_companies=None, lookback_days=7, page_count=100):
        end_date = now_kst().date()
        begin_date = end_date - timedelta(days=max(1, int(lookback_days)))
        companies = [name.strip() for name in (target_companies or []) if name.strip()]

        if not companies:
            rows = self._fetch_list(begin_date, end_date, page_count=page_count)
            return self._normalize_disclosures(rows)

        disclosures = []
        unresolved_companies = []
        for company in companies:
            corp_code = self._find_corp_code(company)
            if not corp_code:
                unresolved_companies.append(company)
                continue

            rows = self._fetch_list(begin_date, end_date, page_count=page_count, corp_code=corp_code)
            disclosures.extend(self._normalize_disclosures(rows, companies=[company]))

        if unresolved_companies:
            rows = self._fetch_list(begin_date, end_date, page_count=page_count)
            disclosures.extend(self._normalize_disclosures(rows, companies=unresolved_companies))

        disclosures = self._deduplicate_disclosures(disclosures)
        return sorted(disclosures, key=lambda item: item.get("received_at") or "", reverse=True)
