import os
from dataclasses import dataclass
from pathlib import Path


NEWS_SECTIONS = [
    {"section": "한국 증시 주요 뉴스", "query": "한국 증시", "display": 5},
    {"section": "미국 증시 주요 뉴스", "query": "미국 증시 뉴욕증시", "display": 5},
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
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_chat_ids: list
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
    codex_timeout_seconds: int

    def missing_required(self, send_telegram=True):
        missing = []
        if not self.naver_client_id:
            missing.append("NAVER_CLIENT_ID")
        if not self.naver_client_secret:
            missing.append("NAVER_CLIENT_SECRET")
        if send_telegram and not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if send_telegram and not self.telegram_chat_ids:
            missing.append("TELEGRAM_CHAT_ID or TELEGRAM_CHAT_IDS")
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


def load_config():
    _load_dotenv_if_available()

    base_dir = Path(os.getenv("APP_BASE_DIR", Path.cwd())).resolve()
    data_dir = base_dir / "data"
    logs_dir = base_dir / "logs"
    output_dir = base_dir / "output"

    target_companies = os.getenv("DART_TARGET_COMPANIES", "싸이토젠,경인양행")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    telegram_chat_ids_raw = os.getenv("TELEGRAM_CHAT_IDS", "").strip() or telegram_chat_id

    return AppConfig(
        base_dir=base_dir,
        naver_client_id=os.getenv("NAVER_CLIENT_ID", "").strip(),
        naver_client_secret=os.getenv("NAVER_CLIENT_SECRET", "").strip(),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=telegram_chat_id,
        telegram_chat_ids=_unique(_split_csv(telegram_chat_ids_raw)),
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
        codex_timeout_seconds=_get_int("CODEX_TIMEOUT_SECONDS", 300),
    )
