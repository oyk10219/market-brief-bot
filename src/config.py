import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DART_TARGET_COMPANIES = "싸이토젠,경인양행"

NEWS_SECTIONS = [
    {"section": "한국 증시 주요 뉴스", "query": "한국 증시", "display": 5},
    {"section": "미국 증시 주요 뉴스", "query": "뉴욕증시 나스닥 S&P500 다우 연준", "display": 5},
    {"section": "IT 관련 뉴스", "query": "IT 기술 AI 소프트웨어 클라우드 보안", "display": 5},
    {"section": "오늘 강한 테마 후보", "query": "증시 강한 테마", "display": 5},
    {"section": "반도체 관련 뉴스", "query": "반도체 주식", "display": 5},
    {"section": "바이오 관련 뉴스", "query": "바이오 주식", "display": 5},
    {"section": "싸이토젠 뉴스", "query": "싸이토젠", "display": 5},
    {"section": "경인양행 뉴스", "query": "경인양행", "display": 5},
]


@dataclass
class AppConfig:
    base_dir: Path
    naver_client_id: str
    naver_client_secret: str
    send_channels: list
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_chat_ids: list
    telegram_admin_chat_id: str
    kakao_rest_api_key: str
    kakao_refresh_token: str
    kakao_redirect_uri: str
    kakao_client_secret: str
    kakao_link_url: str
    kakao_max_text_length: int
    dart_api_key: str
    data_dir: Path
    logs_dir: Path
    output_dir: Path
    db_path: Path
    log_file: Path
    request_timeout: int
    dart_lookback_days: int
    dart_target_companies: list
    summary_provider: str
    codex_model: str
    codex_reasoning_effort: str
    codex_timeout_seconds: int
    article_fetch_enabled: bool
    article_fetch_per_section: int
    article_fetch_max_chars: int
    article_fetch_timeout: int
    news_filter_enabled: bool
    telegram_detail_mode: str
    telegram_links_per_section: int

    def missing_required(self, send_telegram=True, send_kakao=False):
        missing = []
        if not self.naver_client_id:
            missing.append("NAVER_CLIENT_ID")
        if not self.naver_client_secret:
            missing.append("NAVER_CLIENT_SECRET")
        if (send_telegram or send_kakao) and not set(self.send_channels).intersection(("telegram", "kakao")):
            missing.append("SEND_CHANNELS must include telegram or kakao")
        if send_telegram and not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if send_telegram and not self.telegram_chat_ids:
            missing.append("TELEGRAM_CHAT_ID or TELEGRAM_CHAT_IDS")
        if send_kakao and not self.kakao_rest_api_key:
            missing.append("KAKAO_REST_API_KEY")
        if send_kakao and not self.kakao_refresh_token:
            missing.append("KAKAO_REFRESH_TOKEN")
        return missing


def _load_dotenv_if_available():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _get_int(name, default):
    raw_value = os.getenv(name)
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _get_bool(name, default=False):
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    return raw_value.strip().lower() in ("1", "true", "yes", "y", "on")


def _split_csv(value):
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _unique(values):
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _send_channels():
    raw_value = os.getenv("SEND_CHANNELS", "telegram")
    channels = [value.lower() for value in _split_csv(raw_value)]
    return _unique(channels) or ["telegram"]


def load_config():
    _load_dotenv_if_available()

    base_dir = Path(os.getenv("APP_BASE_DIR", Path.cwd())).resolve()
    data_dir = base_dir / "data"
    logs_dir = base_dir / "logs"
    output_dir = base_dir / "output"

    target_companies = os.getenv("DART_TARGET_COMPANIES", DEFAULT_DART_TARGET_COMPANIES)
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    telegram_chat_ids_raw = os.getenv("TELEGRAM_CHAT_IDS", "").strip() or telegram_chat_id

    return AppConfig(
        base_dir=base_dir,
        naver_client_id=os.getenv("NAVER_CLIENT_ID", "").strip(),
        naver_client_secret=os.getenv("NAVER_CLIENT_SECRET", "").strip(),
        send_channels=_send_channels(),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=telegram_chat_id,
        telegram_chat_ids=_unique(_split_csv(telegram_chat_ids_raw)),
        telegram_admin_chat_id=os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip(),
        kakao_rest_api_key=os.getenv("KAKAO_REST_API_KEY", "").strip(),
        kakao_refresh_token=os.getenv("KAKAO_REFRESH_TOKEN", "").strip(),
        kakao_redirect_uri=os.getenv("KAKAO_REDIRECT_URI", "http://localhost:8765/kakao/callback").strip(),
        kakao_client_secret=os.getenv("KAKAO_CLIENT_SECRET", "").strip(),
        kakao_link_url=os.getenv("KAKAO_LINK_URL", "https://github.com/oyk10219/market-brief-bot").strip(),
        kakao_max_text_length=_get_int("KAKAO_MAX_TEXT_LENGTH", 200),
        dart_api_key=os.getenv("DART_API_KEY", "").strip(),
        data_dir=data_dir,
        logs_dir=logs_dir,
        output_dir=output_dir,
        db_path=data_dir / "briefing.db",
        log_file=logs_dir / "app.log",
        request_timeout=_get_int("REQUEST_TIMEOUT", 15),
        dart_lookback_days=_get_int("DART_LOOKBACK_DAYS", 7),
        dart_target_companies=_split_csv(target_companies),
        summary_provider=os.getenv("SUMMARY_PROVIDER", "").strip().lower(),
        codex_model=os.getenv("CODEX_MODEL", "gpt-5.2").strip() or "gpt-5.2",
        codex_reasoning_effort=os.getenv("CODEX_REASONING_EFFORT", "low").strip().lower() or "low",
        codex_timeout_seconds=_get_int("CODEX_TIMEOUT_SECONDS", 600),
        article_fetch_enabled=_get_bool("ARTICLE_FETCH_ENABLED", True),
        article_fetch_per_section=_get_int("ARTICLE_FETCH_PER_SECTION", 3),
        article_fetch_max_chars=_get_int("ARTICLE_FETCH_MAX_CHARS", 2500),
        article_fetch_timeout=_get_int("ARTICLE_FETCH_TIMEOUT", 10),
        news_filter_enabled=_get_bool("NEWS_FILTER_ENABLED", True),
        telegram_detail_mode=os.getenv("TELEGRAM_DETAIL_MODE", "compact").strip().lower() or "compact",
        telegram_links_per_section=_get_int("TELEGRAM_LINKS_PER_SECTION", 1),
    )
