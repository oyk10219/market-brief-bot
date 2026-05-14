import argparse
import os
import sys
import traceback

from .config import NEWS_SECTIONS, load_config
from .article_fetcher import enrich_news_with_articles
from .dart_fetcher import DartFetcher
from .database import BriefingDatabase
from .formatter import format_briefing, format_compact_briefing, split_message
from .kakao_sender import KakaoSender
from .logger import setup_logger
from .news_filter import filter_news_items
from .news_fetcher import NewsFetcher
from .summarizer import summarize_with_codex
from .telegram_sender import TelegramSender
from .utils import deduplicate_news, mask_secret, now_kst


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Market Brief daily briefing bot")
    parser.add_argument("--dry-run", action="store_true", help="텔레그램 전송 없이 콘솔에 출력합니다.")
    parser.add_argument("--no-telegram", action="store_true", help="외부 전송 없이 메시지 생성까지만 수행합니다.")
    parser.add_argument("--debug", action="store_true", help="상세 로그를 출력합니다.")
    parser.add_argument("--keyword", help="지정한 키워드 하나만 테스트합니다.")
    parser.add_argument("--save-md", action="store_true", help="output/briefing_YYYYMMDD.md 파일을 저장합니다.")
    parser.add_argument("--no-summary", action="store_true", help="요약 생성을 건너뜁니다.")
    return parser.parse_args(argv)


def _clear_blocked_local_proxy_env():
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        value = os.environ.get(name, "")
        if "127.0.0.1:9" in value or "localhost:9" in value:
            os.environ.pop(name, None)


def _record_error(db, run_id, logger, stage, exc):
    text = "%s: %s" % (exc.__class__.__name__, exc)
    trace = traceback.format_exc()
    logger.error("[%s] %s", stage, text)
    logger.debug(trace)
    db.record_error(run_id, stage, text, trace)
    return {"stage": stage, "message": text}


def _record_plain_error(db, run_id, logger, stage, message):
    logger.error("[%s] %s", stage, message)
    db.record_error(run_id, stage, message)
    return {"stage": stage, "message": message}


def _selected_sections(keyword):
    if keyword:
        return [{"section": "키워드 테스트: %s" % keyword, "query": keyword, "display": 10}]
    return NEWS_SECTIONS


def _save_markdown(output_dir, message, generated_at):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / ("briefing_%s.md" % generated_at.strftime("%Y%m%d"))
    path.write_text(message + "\n", encoding="utf-8")
    return path


def _masked_chat_id(chat_id):
    return mask_secret(chat_id, visible=4)


def _admin_chat_id(config):
    if config.telegram_admin_chat_id:
        return config.telegram_admin_chat_id
    if config.telegram_chat_ids:
        return config.telegram_chat_ids[0]
    return ""


def _format_failure_alert(status, generated_at, error_summaries, run_id=None):
    lines = [
        "MarketBriefBot 오류 알림",
        "상태: %s" % status,
        "시간: %s" % generated_at.strftime("%Y-%m-%d %H:%M"),
    ]
    if run_id:
        lines.append("실행 ID: %s" % run_id)

    lines.append("")
    lines.append("오류 단계:")
    if error_summaries:
        for error in error_summaries[:8]:
            message = str(error.get("message") or "").replace("\n", " ").strip()
            if len(message) > 300:
                message = message[:300] + "..."
            lines.append("- %s: %s" % (error.get("stage") or "unknown", message))
    else:
        lines.append("- 상세 오류는 logs/app.log 또는 SQLite errors 테이블을 확인해 주세요.")

    return "\n".join(lines)


def _send_failure_alert(config, logger, status, generated_at, error_summaries, run_id=None):
    chat_id = _admin_chat_id(config)
    if not config.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN이 없어 실패 알림을 보낼 수 없습니다.")
        return False
    if not chat_id:
        logger.warning("관리자 chat_id가 없어 실패 알림을 보낼 수 없습니다.")
        return False

    try:
        sender = TelegramSender(config.telegram_bot_token, timeout=config.request_timeout)
        sender.send_message(chat_id, _format_failure_alert(status, generated_at, error_summaries, run_id=run_id))
        logger.info("실패 알림 전송 완료: %s", _masked_chat_id(chat_id))
        return True
    except Exception as exc:
        logger.error("실패 알림 전송 실패: %s: %s", exc.__class__.__name__, exc)
        logger.debug(traceback.format_exc())
        return False


def run(argv=None):
    _clear_blocked_local_proxy_env()
    args = parse_args(argv)
    config = load_config()
    logger = setup_logger(debug=args.debug, log_file=config.log_file)

    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    db = BriefingDatabase(config.db_path)
    db.init_schema()
    run_id = db.start_run()
    if db.disabled:
        logger.warning("SQLite DB disabled; DB writes will be skipped. reason=%s", db.error_message)

    generated_at = now_kst()
    errors = 0
    critical_failure = False
    news_items = []
    disclosures = []
    messages = []
    summary = ""
    error_summaries = []
    send_messages = not args.dry_run and not args.no_telegram
    send_telegram = send_messages and "telegram" in config.send_channels
    send_kakao = send_messages and "kakao" in config.send_channels

    try:
        missing = config.missing_required(send_telegram=send_telegram, send_kakao=send_kakao)
        if send_messages and not (send_telegram or send_kakao):
            missing.append("SEND_CHANNELS must include telegram or kakao")
        if missing:
            message = "필수 환경변수가 누락되었습니다: %s" % ", ".join(missing)
            error_summaries.append(_record_plain_error(db, run_id, logger, "config", message))
            db.finish_run(run_id, "FAILED", 0, 0)
            if send_messages:
                _send_failure_alert(config, logger, "FAILED", generated_at, error_summaries, run_id=run_id)
            return 2

        logger.info("뉴스 수집을 시작합니다.")
        news_fetcher = NewsFetcher(
            config.naver_client_id,
            config.naver_client_secret,
            timeout=config.request_timeout,
        )

        for section_config in _selected_sections(args.keyword):
            section = section_config["section"]
            query = section_config["query"]
            try:
                logger.info("Naver 뉴스 수집: %s", section)
                fetched = news_fetcher.fetch(query, display=section_config.get("display", 5))
                for item in fetched:
                    item["section"] = section
                news_items.extend(fetched)
            except Exception as exc:
                errors += 1
                error_summaries.append(_record_error(db, run_id, logger, "news:%s" % section, exc))

        news_items = deduplicate_news(news_items)
        if config.news_filter_enabled:
            before_filter_count = len(news_items)
            filter_result = filter_news_items(news_items)
            news_items = filter_result["kept"]
            removed_count = len(filter_result["removed"])
            logger.info("뉴스 품질 필터 완료: 유지 %s건, 제외 %s건", len(news_items), removed_count)
            for section, count in sorted(filter_result["removed_by_section"].items()):
                logger.info("뉴스 품질 필터 제외: %s %s건", section, count)
            if before_filter_count and not news_items:
                logger.warning("뉴스 품질 필터 후 남은 뉴스가 없습니다. 필터를 적용하지 않은 목록으로 복구합니다.")
                news_items = filter_result["removed"]
        db.insert_news_items(news_items)
        logger.info("뉴스 수집 완료: %s건", len(news_items))

        if config.article_fetch_enabled and news_items:
            try:
                logger.info(
                    "기사 본문 추출을 시작합니다. 섹션별 최대 %s건",
                    config.article_fetch_per_section,
                )
                article_result = enrich_news_with_articles(
                    news_items,
                    per_section=config.article_fetch_per_section,
                    timeout=config.article_fetch_timeout,
                    max_chars=config.article_fetch_max_chars,
                    logger=logger,
                )
                logger.info(
                    "기사 본문 추출 완료: 성공 %s건, 실패 %s건",
                    article_result["enriched"],
                    article_result["failed"],
                )
            except Exception as exc:
                errors += 1
                error_summaries.append(_record_error(db, run_id, logger, "article_fetch", exc))
                logger.warning("기사 본문 추출에 실패해 검색 요약 기준으로 진행합니다.")

        if config.dart_api_key and config.dart_target_companies:
            try:
                logger.info("OpenDART 공시 수집을 시작합니다.")
                dart_fetcher = DartFetcher(
                    config.dart_api_key,
                    timeout=config.request_timeout,
                    corp_code_cache_path=config.data_dir / "dart_corp_codes.json",
                )
                disclosures = dart_fetcher.fetch_recent_disclosures(
                    target_companies=config.dart_target_companies,
                    lookback_days=config.dart_lookback_days,
                )
                logger.info("OpenDART 공시 수집 완료: %s건", len(disclosures))
            except Exception as exc:
                errors += 1
                error_summaries.append(_record_error(db, run_id, logger, "dart", exc))
        else:
            if not config.dart_api_key:
                logger.info("DART_API_KEY가 없어 공시 수집 단계를 건너뜁니다.")
            else:
                logger.info("DART_TARGET_COMPANIES가 없어 공시 수집 단계를 건너뜁니다.")

        if not news_items and not disclosures:
            critical_failure = True
            errors += 1
            error_summaries.append(
                _record_plain_error(db, run_id, logger, "data", "전송할 뉴스/공시 데이터가 없습니다.")
            )

        if not args.no_summary and config.summary_provider:
            if config.summary_provider == "codex":
                try:
                    logger.info("Codex CLI 요약 생성을 시작합니다.")
                    summary_result = summarize_with_codex(
                        news_items,
                        disclosures,
                        config.output_dir,
                        generated_at,
                        model=config.codex_model or None,
                        reasoning_effort=config.codex_reasoning_effort or "low",
                        timeout=config.codex_timeout_seconds,
                        cwd=config.base_dir,
                    )
                    summary = summary_result.summary
                    logger.info("Codex CLI 요약 생성 완료: %s", summary_result.output_path)
                except Exception as exc:
                    errors += 1
                    error_summaries.append(_record_error(db, run_id, logger, "summary:codex", exc))
                    logger.warning("요약 생성에 실패해 기존 뉴스 목록만 전송합니다.")
            else:
                logger.warning("지원하지 않는 SUMMARY_PROVIDER입니다: %s", config.summary_provider)

        detailed_briefing = format_briefing(news_items, disclosures, generated_at=generated_at, summary=summary)
        if config.telegram_detail_mode == "compact":
            telegram_briefing = format_compact_briefing(
                news_items,
                disclosures,
                generated_at=generated_at,
                summary=summary,
                links_per_section=config.telegram_links_per_section,
                watchlist_companies=config.dart_target_companies,
            )
        else:
            telegram_briefing = detailed_briefing
        messages = split_message(telegram_briefing)
        kakao_message_count = 0

        if args.save_md:
            path = _save_markdown(config.output_dir, detailed_briefing, generated_at)
            logger.info("Markdown 저장 완료: %s", path)

        if args.dry_run or args.no_telegram:
            logger.info("외부 전송 없이 메시지를 출력합니다.")
            for index, message in enumerate(messages, start=1):
                print("\n----- MESSAGE %s/%s -----\n" % (index, len(messages)))
                print(message)
                db.record_sent_message(run_id, index, message, "DRY_RUN")
        else:
            if send_telegram:
                logger.info(
                    "텔레그램 전송을 시작합니다. 수신자 %s명, 메시지 %s개",
                    len(config.telegram_chat_ids),
                    len(messages),
                )
                sender = TelegramSender(
                    config.telegram_bot_token,
                    timeout=config.request_timeout,
                )
                telegram_failures = 0
                for recipient_index, chat_id in enumerate(config.telegram_chat_ids, start=1):
                    masked_chat_id = _masked_chat_id(chat_id)
                    try:
                        logger.info(
                            "텔레그램 수신자 %s/%s 전송 시작: %s",
                            recipient_index,
                            len(config.telegram_chat_ids),
                            masked_chat_id,
                        )
                        results = sender.send_messages(chat_id, messages)
                        for index, result in enumerate(results, start=1):
                            db.record_sent_message(
                                run_id,
                                index,
                                messages[index - 1],
                                "SENT",
                                telegram_message_id=str(result.get("message_id", "")),
                            )
                        logger.info(
                            "텔레그램 수신자 %s/%s 전송 완료",
                            recipient_index,
                            len(config.telegram_chat_ids),
                        )
                    except Exception as exc:
                        errors += 1
                        telegram_failures += 1
                        error_summaries.append(_record_error(db, run_id, logger, "telegram:%s" % masked_chat_id, exc))
                        for index, message in enumerate(messages, start=1):
                            db.record_sent_message(run_id, index, message, "FAILED")

                if telegram_failures == len(config.telegram_chat_ids):
                    critical_failure = True
                elif telegram_failures:
                    logger.warning(
                        "텔레그램 일부 수신자 전송 실패: %s/%s명",
                        telegram_failures,
                        len(config.telegram_chat_ids),
                    )
                else:
                    logger.info("텔레그램 전송 완료")

            if send_kakao:
                try:
                    kakao_sender = KakaoSender(
                        config.kakao_rest_api_key,
                        config.kakao_refresh_token,
                        client_secret=config.kakao_client_secret,
                        link_url=config.kakao_link_url,
                        timeout=config.request_timeout,
                        max_text_length=config.kakao_max_text_length,
                    )
                    kakao_messages = kakao_sender.split_message(telegram_briefing)
                    kakao_message_count = len(kakao_messages)
                    logger.info("카카오톡 나에게 보내기를 시작합니다. 메시지 %s개", len(kakao_messages))
                    results = kakao_sender.send_message(telegram_briefing)
                    for index, message in enumerate(kakao_messages, start=1):
                        db.record_sent_message(run_id, index, message, "KAKAO_SENT")
                    logger.info("카카오톡 나에게 보내기 완료: %s개", len(results))
                except Exception as exc:
                    errors += 1
                    error_summaries.append(_record_error(db, run_id, logger, "kakao", exc))
                    critical_failure = critical_failure or not send_telegram

        if critical_failure:
            status = "FAILED"
        elif errors:
            status = "PARTIAL_FAILED"
        else:
            status = "SUCCESS"

        db.finish_run(
            run_id,
            status,
            item_count=len(news_items) + len(disclosures),
            message_count=(
                (len(messages) * len(config.telegram_chat_ids) if send_telegram else 0)
                + kakao_message_count
                + (len(messages) if not send_messages else 0)
            ),
        )

        if send_messages and status != "SUCCESS":
            _send_failure_alert(config, logger, status, generated_at, error_summaries, run_id=run_id)

        if critical_failure:
            return 1
        return 0
    except Exception as exc:
        error_summaries.append(_record_error(db, run_id, logger, "unexpected", exc))
        db.finish_run(
            run_id,
            "FAILED",
            item_count=len(news_items) + len(disclosures),
            message_count=len(messages),
        )
        if send_messages:
            _send_failure_alert(config, logger, "FAILED", generated_at, error_summaries, run_id=run_id)
        return 1


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
