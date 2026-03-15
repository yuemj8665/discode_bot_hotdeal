# 변경 로그

프로젝트 변경 내용을 날짜 기준으로 기록합니다.

---

## 변경 로그 템플릿

```
### [YYYY-MM-DD] 변경 제목
- **변경 유형**: 기능 추가 / 버그 수정 / 리팩토링 / 설정 변경
- **변경 내용**:
- **변경 이유**:
- **영향 범위**:
```

---

## 변경 이력

### [2026-03-15] AI 분석 실패 시 재시도 정책 추가
- **변경 유형**: 기능 추가
- **변경 내용**:
  - `database/models.py`: `PendingAnalysis`에 `retry_count` 필드 추가
  - `database/db.py`: `pending_analysis` 테이블에 `retry_count` 컬럼 추가 (마이그레이션 포함), `reschedule_failed_analysis()` 메서드 추가
  - `services/analysis_service.py`: 실패 시 `retry_count < 3`이면 5분 후 재시도 예약, 3회 초과 시 `failed`로 확정
- **변경 이유**: Gemini API 일시 오류 발생 시 분석이 영구 실패(`failed`)로 고착되는 문제 방지
- **영향 범위**: `database/`, `services/analysis_service.py`
- **재시도 정책**: 최대 3회, 실패 시 5분 후 `pending`으로 복귀 → `scheduled_at` 갱신

---

### [2026-03-15] Anthropic → Google Gemini 2.5 Flash AI 분석 기능 교체
- **변경 유형**: 기능 변경
- **변경 내용**:
  - `services/ai_client.py`: `anthropic` SDK → `google-genai` SDK로 전면 교체, 비동기 `client.aio.models.generate_content` 사용, JSON 코드블록 파싱 처리 추가
  - `config/settings.py`: `ANTHROPIC_API_KEY` → `GEMINI_API_KEY`
  - `bot.py`: `Settings.ANTHROPIC_API_KEY` → `Settings.GEMINI_API_KEY` (3곳)
  - `services/crawl_service.py`: `Settings.ANTHROPIC_API_KEY` → `Settings.GEMINI_API_KEY`
  - `requirements.txt`: `google-genai>=1.0.0` 추가
  - `.env.example`: `GEMINI_API_KEY` 항목 및 발급 URL 업데이트
  - `k8s/base/configmap.yaml`: 주석 업데이트
  - `k8s/overlays/dev/kustomization.yaml`: 이미지 태그 `20260315_1900`으로 업데이트
- **변경 이유**: Anthropic API Key 미발급 상태. Google Gemini 1.5 Flash 무료 티어(1500 req/day) 활용으로 비용 0원 운영 가능. 실제 사용량(하루 ~25건)은 무료 한도의 약 1.7%
- **영향 범위**: `services/`, `config/`, `bot.py`, `requirements.txt`, `.env.example`, `k8s/`
- **활성화 조건**: `.env` 또는 k8s Secret에 `GEMINI_API_KEY` 설정 시 자동 활성화
- **사용 모델**: `gemini-2.5-flash` (gemini-1.5-flash, gemini-2.0-flash는 해당 계정에서 미지원)

---

### [2026-03-15] AI 분석 기능 환경변수 설정 추가
- **변경 유형**: 설정 변경
- **변경 내용**:
  - `.env.example`: `ANTHROPIC_API_KEY`, `AI_ANALYSIS_DELAY_HOURS` 항목 추가 (주석 포함)
  - `k8s/base/configmap.yaml`: `AI_ANALYSIS_DELAY_HOURS` 추가
  - `ANTHROPIC_API_KEY`는 민감 값이므로 k8s Secret(`hotdeal-bot-secret`)에 별도 주입 방식으로 결정
- **변경 이유**: AI 분석 기능 구현 후 실제 API Key 입력 경로가 `.env.example`과 k8s 설정에 누락되어 있었음
- **영향 범위**: `.env.example`, `k8s/base/configmap.yaml`
- **API Key 주입 방법**:
  - 로컬: `.env` 파일에 `ANTHROPIC_API_KEY=sk-ant-...` 직접 입력
  - k8s: `kubectl patch secret dev-hotdeal-bot-secret -n hotdeal-bot-dev` 명령으로 Secret에 주입 후 Pod 재시작

---

### [2026-03-15] AI 분석 기능 구조 구현 (stub)
- **변경 유형**: 기능 추가
- **변경 내용**:
  - `config/settings.py`: `ANTHROPIC_API_KEY`, `AI_ANALYSIS_DELAY_HOURS` 환경 변수 추가
  - `database/models.py`: `PendingAnalysis` dataclass 추가
  - `database/db.py`:
    - `pending_analysis` 테이블 (분석 대기 항목), `notification_history` 테이블 (알림 수신 이력) 추가
    - `users` 테이블에 `ai_analysis_alert` BOOLEAN 컬럼 마이그레이션
    - `schedule_analysis`, `get_due_analyses`, `update_analysis_status`, `record_notification`, `get_notified_users`, `cleanup_old_analyses` 메서드 추가
  - `services/ai_client.py` (신규): Anthropic API 호출 클라이언트. `ANTHROPIC_API_KEY` 미설정 시 완전 비활성화
  - `services/analysis_service.py` (신규): 대기 분석 항목 처리 서비스. `get_due_analyses` → `fetch_post_detail` → `analyze_hotdeal` → `send_analysis_result` 흐름
  - `crawling/crawler.py`: `fetch_post_detail()`, `_parse_post_detail()` 추가 (추천수, 댓글 최대 30개 수집)
  - `services/crawl_service.py`: 알림 발송 후 `schedule_analysis` + `record_notification` 자동 예약 (API Key 있을 때만)
  - `services/notification_service.py`: `send_analysis_result()`, `_build_analysis_embed()` 추가 (추천/비추천 색상 구분 Embed)
  - `bot.py`: `analysis_task` (`@tasks.loop(minutes=5)`) 추가, `on_ready`에서 시작
- **변경 이유**: 핫딜 알림 후 3시간 뒤 추천수·댓글 수를 재크롤링하여 Claude AI가 추천/비추천 판단 및 이유를 2차 알림으로 전송하는 기능 기획. API Key 미발급 상태이므로 현재 봇 동작에 영향 없이 구조만 구현
- **영향 범위**: `config/`, `database/`, `crawling/`, `services/`, `bot.py`
- **활성화 조건**: `.env`에 `ANTHROPIC_API_KEY` 설정 시 자동 활성화

---

### [2026-03-15] 테스트 결과 파일 형식 개선
- **변경 유형**: 문서 개선
- **변경 내용**:
  - `docs/test_results/test_20260315_1530.md` 형식 개선
    - 테스트 요약에 `Exit Code` 항목 추가 (0 = 전체 통과)
    - 실행 로그에 `Process finished with exit code 0` 및 Exit Code 코드표 추가
    - 테스트 상세를 테이블 형식(테스트명 / 요청 / 응답 / 결과)으로 재구성
- **변경 이유**: 테스트 결과 파일에 실제 요청/응답 로그와 프로세스 종료 코드를 포함해 가독성 향상
- **영향 범위**: `docs/test_results/`

---

### [2026-03-15] 로컬 Docker 컨테이너 중지 (중복 인스턴스 제거)
- **변경 유형**: 운영 설정 변경
- **변경 내용**:
  - `docker compose -f docker-compose.yaml down`으로 로컬 `hotdeal-bot` 컨테이너 중지
- **변경 이유**: k8s Pod + 로컬 Docker 컨테이너 동시 실행으로 `!ping` 등 명령어 응답이 두 번씩 오는 문제 발생
- **영향 범위**: 운영 환경 (로컬 Docker). k8s Pod는 영향 없음

---

### [2026-03-15] 카테고리 구독 기능 추가
- **변경 유형**: 기능 추가
- **변경 내용**:
  - `database/models.py`: `Category` dataclass 추가
  - `database/db.py`: `user_categories` 테이블 추가 및 CRUD 메서드 구현
    - `add_category`, `get_categories`, `delete_category`, `get_all_categories`, `get_users_by_category`
  - `commands/category.py`: `!카테고리 추가/삭제/목록` 명령어 신규 구현
  - `services/crawl_service.py`: `send_keyword_notifications` → `send_notifications` 리네임, 카테고리 매칭 로직 추가
  - `services/notification_service.py`: Embed에 "매칭된 카테고리" 필드 추가, 알림 제목 변경
  - `bot.py`: `CategoryCommands` Cog 등록
  - `tests/integration/test_database.py`: `TestCategory` 클래스 8개 테스트 추가 (총 73개 통과)
- **변경 이유**: 키워드 매칭 외에 카테고리 구독 기능 요구 (식품/전자제품/PC 등 11개 카테고리)
- **영향 범위**: `database/`, `commands/`, `services/`, `bot.py`, `tests/`

---

### [2026-03-11] 코드 품질 개선 및 테스트 구축
- **변경 유형**: 버그 수정, 리팩토링, 테스트
- **변경 내용**:
  - `.gitignore`에 `CLAUDE.md` 추가 (git 추적 제외)
  - `HotdealCrawler.crawl()`, `crawl_with_keyword_check()` 삭제 (데드코드 — `CrawlService`가 동일 역할 수행)
  - 미사용 import `urlparse`, `datetime` 제거 (`crawler.py`)
  - `CrawlService._filter_by_url()` 버그 수정: 마지막 URL 발견 후 `continue` → `break` (이전 게시글까지 새것으로 처리하던 문제)
  - `CrawlService.run()` 버그 수정: `save_posts(all_posts)` → `save_posts(new_posts)` (매 크롤링마다 전체 게시글 DB write 반복 문제)
  - `bot.py` `on_ready` 중복 로드 방지: `bot.extensions` 체크 후 로드
  - `bot.py` deprecated API 수정: `bot.loop.run_until_complete()` → `asyncio.run()`
  - 테스트 구축: 유닛 37개 + 통합 28개 = 총 65개 (모두 통과)
    - `tests/unit/test_crawler.py`: `check_keywords`, `parse`, `_extract_price_numeric`, `_get_full_url`
    - `tests/unit/test_crawl_service.py`: 필터링 로직 전체
    - `tests/integration/test_database.py`: DB CRUD 전체 (`hotdeal_test` DB 사용)
- **변경 이유**: 버그 수정, DB 부하 감소, reconnect 안정성 확보, 미래 Python 버전 대응
- **영향 범위**: `crawler.py`, `crawl_service.py`, `bot.py`, `tests/`

### [2026-03-11] 서비스 레이어 분리 및 문서화
- **변경 유형**: 리팩토링, 문서화
- **변경 내용**:
  - `bot.py`의 크롤링/알림 로직을 `services/` 레이어로 분리
    - `CrawlService`: fetch → filter → save → notify 파이프라인 담당
    - `NotificationService`: Discord DM / 채널 알림 전송 담당
  - `crawl_state` 테이블에 `last_post_url`, `last_post_datetime` 컬럼 추가
  - datetime 기반 중복 게시글 필터링 로직 추가 (datetime > URL > post ID 폴백)
  - `docs/` 폴더 생성 (error_log.md, change_log.md)
  - `README.md` 규정 목차에 맞게 재구성
- **변경 이유**: 코드 책임 분리, 유지보수성 향상, 문서 규정 준수
- **영향 범위**: `bot.py`, `services/`, `database/db.py`, `README.md`

### [초기] 프로젝트 초기화
- **변경 유형**: 기능 추가
- **변경 내용**:
  - Discord 봇 기본 구조 설정 (discord.py)
  - Arca Live 핫딜 크롤러 구현 (aiohttp + BeautifulSoup)
  - PostgreSQL 비동기 연결 (asyncpg)
  - 키워드 CRUD 명령어 구현 (`!키워드 추가/삭제/목록`)
  - Docker Compose, Kubernetes(ArgoCD) 배포 설정
- **영향 범위**: 전체
