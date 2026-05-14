from io import BytesIO
import zipfile

from src import dart_fetcher as dart_module
from src.dart_fetcher import DartFetcher


class FakeResponse:
    def __init__(self, status_code=200, payload=None, content=b"", text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content
        self.text = text

    def json(self):
        return self._payload


def _corp_code_zip():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<result>
  <list>
    <corp_code>00126380</corp_code>
    <corp_name>싸이토젠</corp_name>
    <stock_code>217330</stock_code>
    <modify_date>20250101</modify_date>
  </list>
</result>
"""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("CORPCODE.xml", xml.encode("utf-8"))
    return buffer.getvalue()


def test_fetch_recent_disclosures_queries_by_corp_code(monkeypatch, tmp_path):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append((url, dict(params or {})))
        if url == DartFetcher.DART_CORP_CODE_URL:
            return FakeResponse(content=_corp_code_zip())
        return FakeResponse(
            payload={
                "status": "000",
                "list": [
                    {
                        "corp_name": "싸이토젠",
                        "report_nm": "주요사항보고서",
                        "rcept_dt": "20260514",
                        "rcept_no": "20260514000123",
                        "flr_nm": "싸이토젠",
                        "stock_code": "217330",
                    }
                ],
            }
        )

    monkeypatch.setattr(dart_module.requests, "get", fake_get)

    fetcher = DartFetcher("secret", timeout=1, corp_code_cache_path=tmp_path / "dart_corp_codes.json")
    rows = fetcher.fetch_recent_disclosures(["싸이토젠"], lookback_days=7)

    assert calls[0][0] == DartFetcher.DART_CORP_CODE_URL
    assert calls[1][0] == DartFetcher.DART_LIST_URL
    assert calls[1][1]["corp_code"] == "00126380"
    assert rows[0]["corp_name"] == "싸이토젠"
    assert rows[0]["link"].endswith("20260514000123")


def test_fetch_recent_disclosures_returns_empty_for_no_data(monkeypatch, tmp_path):
    def fake_get(url, params=None, timeout=None):
        if url == DartFetcher.DART_CORP_CODE_URL:
            return FakeResponse(content=_corp_code_zip())
        return FakeResponse(payload={"status": "013", "message": "조회된 데이타가 없습니다."})

    monkeypatch.setattr(dart_module.requests, "get", fake_get)

    fetcher = DartFetcher("secret", timeout=1, corp_code_cache_path=tmp_path / "dart_corp_codes.json")

    assert fetcher.fetch_recent_disclosures(["싸이토젠"], lookback_days=7) == []
