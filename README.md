# Market Brief Bot

Windows 작업 스케줄러 또는 GitHub Actions 수동 실행으로 텔레그램/카카오톡에 주식/IT 뉴스 브리핑을 보내는 MVP입니다.

이 프로그램은 투자 추천 서비스가 아니라 뉴스/공시 정보 정리 도구입니다. 매수, 매도, 목표가, 손절가 문구는 포함하지 않습니다.

## 주요 기능

- Naver Search API 뉴스 수집
- OpenDART API 공시 수집
- Telegram Bot API 메시지 전송
- KakaoTalk 나에게 보내기 옵션
- 제목/링크 기준 중복 제거
- HTML 태그와 엔티티 정리
- 긴 메시지 자동 분할 전송
- 실패/부분실패 시 관리자 텔레그램 알림
- SQLite 로컬 DB 저장
- `--dry-run`, `--no-telegram`, `--debug`, `--keyword`, `--save-md` 옵션 지원
- 로컬 Codex CLI 요약 옵션 지원
- 기사 본문 추출 기반 요약 보강
- 뉴스 품질 필터링
- 텔레그램 compact 브리핑과 상세 Markdown 저장 분리
- Windows 작업 스케줄러 기반 로컬 자동 실행
- GitHub Actions 수동 실행 지원

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
TELEGRAM_CHAT_IDS=
TELEGRAM_ADMIN_CHAT_ID=your_admin_chat_id
SEND_CHANNELS=telegram
DART_API_KEY=your_dart_api_key
```

실행 예시는 아래와 같습니다.

```powershell
python -m src.main --dry-run --debug
python -m src.main --keyword 반도체 --dry-run
python -m src.main --save-md
python -m src.main --no-telegram --save-md
python -m src.main --no-summary --dry-run
```

## 환경변수가 없을 때 동작

- `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`이 없으면 뉴스 수집을 할 수 없어 실행이 실패합니다.
- `SEND_CHANNELS`는 `telegram`, `kakao`, `telegram,kakao` 중 하나로 설정합니다. 기본값은 `telegram`입니다.
- `TELEGRAM_BOT_TOKEN`이 없으면 실제 전송 실행은 실패합니다.
- `TELEGRAM_CHAT_ID` 또는 `TELEGRAM_CHAT_IDS`가 없으면 실제 전송 실행은 실패합니다.
- `SEND_CHANNELS`에 `kakao`가 포함되면 `KAKAO_REST_API_KEY`, `KAKAO_REFRESH_TOKEN`이 필요합니다.
- 단, `--dry-run` 또는 `--no-telegram`에서는 텔레그램 값 없이 메시지 생성 테스트가 가능합니다.
- `DART_API_KEY`가 없으면 공시 수집 단계만 건너뜁니다.
- `TELEGRAM_ADMIN_CHAT_ID`가 있으면 실패/부분실패 알림을 해당 chat_id로 먼저 보냅니다. 없으면 첫 번째 `TELEGRAM_CHAT_ID` 또는 `TELEGRAM_CHAT_IDS` 수신자로 보냅니다.
- `SUMMARY_PROVIDER=codex`이면 로컬 Codex CLI로 요약을 생성합니다. 실패하면 요약 없이 기존 뉴스 목록만 전송합니다.
- 로컬 Codex CLI가 기본 모델 문제로 실패하지 않도록 `CODEX_MODEL=gpt-5.2` 사용을 권장합니다.
- `ARTICLE_FETCH_ENABLED=true`이면 섹션별 상위 기사 본문을 추출해 Codex 요약 근거로 사용합니다. 추출 실패 기사는 기존 검색 요약을 사용합니다.
- `NEWS_FILTER_ENABLED=true`이면 정치/연예/스포츠 등 관련성이 낮은 기사와 섹션 주제에 맞지 않는 기사를 제외합니다. 문제가 있으면 `false`로 끌 수 있습니다.
- `TELEGRAM_DETAIL_MODE=compact`이면 텔레그램에는 핵심 요약, 오늘 볼 테마, 주요 기사 링크만 보냅니다. 상세 전체 목록은 `output/briefing_YYYYMMDD.md`에 저장됩니다.

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

여러 사람에게 개인 메시지로 보내려면 각 사용자가 먼저 봇에게 `/start` 또는 아무 메시지를 보내야 합니다. 이후 각 사용자의 `chat.id`를 콤마로 연결해 등록합니다.

```env
TELEGRAM_CHAT_ID=123456789,987654321,555555555
```

또는 아래처럼 별도 변수에 등록할 수 있습니다. `TELEGRAM_CHAT_IDS`가 있으면 이 값을 우선 사용합니다.

```env
TELEGRAM_CHAT_IDS=123456789,987654321,555555555
```

## 카카오톡 나에게 보내기

카카오톡은 공식 REST API의 `나에게 보내기` 기능을 사용합니다. 이 기능은 로그인한 사용자 본인의 "나와의 채팅방"으로만 보낼 수 있습니다. 텍스트 템플릿은 최대 200자 제한이 있어 프로그램이 자동으로 여러 개의 카카오톡 메시지로 나눠 보냅니다.

Kakao Developers에서 아래 설정을 먼저 합니다.

```text
1. 애플리케이션 생성
2. 플랫폼 > Web 플랫폼 등록
3. Redirect URI 등록: http://localhost:8765/kakao/callback
4. 카카오 로그인 활성화
5. 동의항목에서 카카오톡 메시지 전송(talk_message) 동의 설정
6. 제품 연결 또는 Web domain에 KAKAO_LINK_URL 도메인 등록
```

`.env`에는 최소 아래 값을 입력합니다.

```env
SEND_CHANNELS=telegram,kakao
KAKAO_REST_API_KEY=your_kakao_rest_api_key
KAKAO_REDIRECT_URI=http://localhost:8765/kakao/callback
KAKAO_LINK_URL=https://github.com/oyk10219/market-brief-bot
```

그 다음 로컬에서 아래 명령을 실행합니다.

```powershell
.\.venv\Scripts\python.exe scripts\kakao_auth.py
```

브라우저가 열리면 사용자님이 직접 카카오 로그인과 동의를 진행합니다. 완료 후 터미널에 출력되는 값을 `.env`에 추가합니다.

```env
KAKAO_REFRESH_TOKEN=issued_refresh_token
```

Client secret을 켜둔 앱이면 아래 값도 넣습니다.

```env
KAKAO_CLIENT_SECRET=your_kakao_client_secret
```

카카오 공식 문서:

- [KakaoTalk Message REST API](https://developers.kakao.com/docs/latest/en/kakaotalk-message/rest-api)
- [Kakao Login REST API](https://developers.kakao.com/docs/latest/en/kakaologin/rest-api)

## Naver API 키

Naver Developers에서 애플리케이션을 생성하고 Search API 사용 설정 후 아래 값을 등록합니다.

- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`

뉴스 API가 실패하면 해당 단계 오류가 `logs/app.log`와 SQLite `errors` 테이블에 기록됩니다.

## OpenDART API 키

OpenDART에서 인증키를 발급받아 `DART_API_KEY`에 등록합니다.

`DART_API_KEY`가 없거나 `DART_TARGET_COMPANIES`가 비어 있으면 프로그램은 공시 수집을 건너뛰고 뉴스만으로 브리핑을 생성합니다.

기본 관심 공시 대상은 `싸이토젠,경인양행`입니다. 다른 종목으로 바꾸려면 `.env`에서 대상 회사를 콤마로 지정하면 됩니다.

```env
DART_TARGET_COMPANIES=싸이토젠,경인양행
```

공시는 OpenDART 회사코드를 조회한 뒤 회사별로 직접 조회합니다. 회사코드 목록은 최초 실행 시 `data/dart_corp_codes.json`에 캐시되며 Git에는 올라가지 않습니다.

최근 기간에 관심종목 공시가 없으면 텔레그램에는 아래처럼 표시됩니다.

```text
## DART 공시
최근 관심종목 공시는 없습니다.
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

- `SEND_CHANNELS`
- `TELEGRAM_CHAT_IDS`
- `TELEGRAM_ADMIN_CHAT_ID`
- `KAKAO_REST_API_KEY`
- `KAKAO_REFRESH_TOKEN`
- `KAKAO_CLIENT_SECRET`
- `KAKAO_LINK_URL`
- `DART_API_KEY`
- `DART_TARGET_COMPANIES`

여러 개인 수신자에게 보내려면 `TELEGRAM_CHAT_ID` 하나에 콤마로 여러 값을 넣거나, `TELEGRAM_CHAT_IDS` Secret을 추가해서 콤마로 여러 chat_id를 넣으면 됩니다.

실패 알림만 별도 관리자에게 보내려면 `TELEGRAM_ADMIN_CHAT_ID`에 관리자 chat_id를 등록합니다. 등록하지 않으면 첫 번째 일반 수신자에게 실패 알림을 보냅니다.

Secrets가 누락되면 GitHub Actions `Run` 단계에서 어떤 값이 빠졌는지 명확히 출력하고 실패합니다.

## GitHub Actions 실행

수동 실행:

```text
GitHub > Actions > Daily Market Briefing > Run workflow
```

자동 실행:

- GitHub Actions 자동 schedule은 사용하지 않습니다.
- 로컬 Codex 요약을 사용하기 위해 Windows 작업 스케줄러에서 매일 08:30, 13:00에 실행합니다.

## 로컬 Codex 요약 실행

GitHub Actions는 GitHub 서버에서 실행되므로 로컬 Codex 앱이나 CLI를 사용할 수 없습니다. 이 프로젝트는 로컬 Codex 요약을 사용하기 위해 Windows 작업 스케줄러 자동 실행을 기본 방식으로 사용합니다.

```powershell
D:\MarketBriefBot\scripts\run_daily_local.ps1
```

이 스크립트는 아래 순서로 동작합니다.

```text
뉴스/DART 수집
섹션별 상위 기사 본문 추출
Codex CLI 요약 생성
output/codex_prompt_YYYYMMDD_HHMMSS.md 저장
output/codex_summary_YYYYMMDD_HHMMSS.md 저장
요약 + 상세 뉴스 목록 텔레그램 전송
```

기사 본문 추출은 요약 품질을 높이기 위한 용도입니다. 언론사별 HTML 구조나 접근 제한 때문에 일부 기사는 실패할 수 있으며, 실패한 기사는 Naver Search API의 제목/검색 요약을 사용합니다. 추출한 본문은 텔레그램에 원문으로 보내지 않고 Codex 요약 입력에만 사용합니다.

기본 텔레그램 메시지는 읽기 쉬운 compact 형식입니다.

```text
Market Brief
생성 시각

## 핵심 요약
## 오늘 볼 테마
## 주요 기사
## 관심 종목/공시
## DART 공시
```

기본값은 섹션별 링크 1개만 텔레그램에 표시합니다. 섹션별 전체 뉴스 목록은 텔레그램으로 모두 보내지 않고 `output/briefing_YYYYMMDD.md`에 저장합니다.

수동 테스트:

```powershell
powershell.exe -ExecutionPolicy Bypass -File D:\MarketBriefBot\scripts\run_daily_local.ps1 -DryRun
```

실제 전송:

```powershell
powershell.exe -ExecutionPolicy Bypass -File D:\MarketBriefBot\scripts\run_daily_local.ps1
```

Windows 작업 스케줄러 설정 예시:

```text
트리거 1: 매일 08:30
트리거 2: 매일 13:00
동작 프로그램: powershell.exe
인수 추가: -ExecutionPolicy Bypass -File D:\MarketBriefBot\scripts\run_daily_local.ps1
시작 위치: D:\MarketBriefBot
```

주의사항:

- 노트북이 켜져 있고 인터넷이 연결되어 있어야 합니다.
- Codex CLI 로그인이 현재 Windows 사용자 기준으로 유지되어 있어야 합니다.
- PC 절전 상태에서는 실행되지 않을 수 있으므로 전원/절전 설정을 확인해야 합니다.
- GitHub Actions는 자동 schedule 없이 수동 실행만 남겨두었습니다.

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
