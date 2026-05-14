# Market Brief Bot

GitHub Actions에서 매일 아침 텔레그램으로 주식 뉴스와 관심 종목 공시 링크를 보내는 MVP입니다.

이 프로그램은 투자 추천 서비스가 아니라 뉴스/공시 정보 정리 도구입니다. 매수, 매도, 목표가, 손절가 문구는 포함하지 않습니다.

## 주요 기능

- Naver Search API 뉴스 수집
- OpenDART API 공시 수집
- Telegram Bot API 메시지 전송
- 제목/링크 기준 중복 제거
- HTML 태그와 엔티티 정리
- 긴 메시지 자동 분할 전송
- SQLite 로컬 DB 저장
- `--dry-run`, `--no-telegram`, `--debug`, `--keyword`, `--save-md` 옵션 지원
- GitHub Actions 수동 실행 및 평일 오전 8시 30분 KST 자동 실행

## 프로젝트 구조

```text
MarketBriefBot/
  src/
    main.py
    config.py
    news_fetcher.py
    dart_fetcher.py
    formatter.py
    telegram_sender.py
    database.py
    logger.py
    utils.py
  tests/
  data/
  logs/
  output/
  .github/workflows/daily-briefing.yml
```

## 로컬 실행 방법

```powershell
cd D:\MarketBriefBot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

`.env`에 아래 값을 입력합니다.

```env
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
DART_API_KEY=your_dart_api_key
```

실행 예시는 아래와 같습니다.

```powershell
python -m src.main --dry-run --debug
python -m src.main --keyword 반도체 --dry-run
python -m src.main --save-md
python -m src.main --no-telegram --save-md
```

## 환경변수가 없을 때 동작

- `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`이 없으면 뉴스 수집을 할 수 없어 실행이 실패합니다.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`가 없으면 실제 전송 실행은 실패합니다.
- 단, `--dry-run` 또는 `--no-telegram`에서는 텔레그램 값 없이 메시지 생성 테스트가 가능합니다.
- `DART_API_KEY`가 없으면 공시 수집 단계만 건너뜁니다.

## 텔레그램 봇 토큰 얻는 방법

1. 텔레그램에서 `BotFather`를 검색합니다.
2. `/newbot` 명령으로 봇을 생성합니다.
3. 발급된 토큰을 `TELEGRAM_BOT_TOKEN`에 등록합니다.
4. 만든 봇에게 아무 메시지나 보냅니다.
5. 아래 주소를 브라우저에서 열어 `chat.id`를 확인합니다.

```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates
```

확인한 `chat.id` 값을 `TELEGRAM_CHAT_ID`에 등록합니다.

## Naver API 키

Naver Developers에서 애플리케이션을 생성하고 Search API 사용 설정 후 아래 값을 등록합니다.

- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`

뉴스 API가 실패하면 해당 단계 오류가 `logs/app.log`와 SQLite `errors` 테이블에 기록됩니다.

## OpenDART API 키

OpenDART에서 인증키를 발급받아 `DART_API_KEY`에 등록합니다.

`DART_API_KEY`가 없으면 프로그램은 공시 수집을 건너뛰고 뉴스만으로 브리핑을 생성합니다. 기본 관심 공시 대상은 아래 회사입니다.

- 싸이토젠
- 경인양행

대상 회사는 `.env`에서 변경할 수 있습니다.

```env
DART_TARGET_COMPANIES=싸이토젠,경인양행
```

## GitHub Secrets 등록

GitHub 저장소 `market-brief-bot`에서 아래 메뉴로 이동합니다.

```text
Settings > Secrets and variables > Actions > New repository secret
```

필수 Secrets:

- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

선택 Secrets:

- `DART_API_KEY`

Secrets가 누락되면 GitHub Actions `Run` 단계에서 어떤 값이 빠졌는지 명확히 출력하고 실패합니다.

## GitHub Actions 실행

수동 실행:

```text
GitHub > Actions > Daily Market Briefing > Run workflow
```

자동 실행:

- 한국 시간 평일 오전 8시 30분
- GitHub Actions cron 기준: `30 23 * * 0-4`

## DB 조회 방법

로컬 실행 시 `data/briefing.db`가 생성됩니다.

```powershell
sqlite3 data/briefing.db
```

최근 실행 이력:

```sql
SELECT id,
       started_at,
       finished_at,
       status,
       item_count,
       message_count
  FROM briefing_runs
 ORDER BY id DESC
 LIMIT 10;
```

최근 뉴스:

```sql
SELECT section,
       title,
       source,
       published_at,
       link
  FROM news_items
 ORDER BY id DESC
 LIMIT 20;
```

오류 확인:

```sql
SELECT run_id,
       stage,
       message,
       created_at
  FROM errors
 ORDER BY id DESC
 LIMIT 20;
```

텔레그램 전송 기록:

```sql
SELECT run_id,
       message_part,
       status,
       telegram_message_id,
       sent_at
  FROM sent_messages
 ORDER BY id DESC
 LIMIT 20;
```

## 테스트

```powershell
pytest
```

## 보안 주의사항

- API 키와 토큰은 코드에 하드코딩하지 않습니다.
- `.env`, `logs`, `data/*.db`, `output`은 GitHub에 올리지 않도록 `.gitignore`에 등록되어 있습니다.
- 로그에는 토큰 전체를 출력하지 않습니다.
