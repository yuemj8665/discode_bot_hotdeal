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

### [2026-04-23] Gemini 503 에러 발생 시 다른 키로 즉시 1회 재시도
- **변경 유형**: 버그 수정
- **변경 내용**:
  - `services/ai_client.py`: 503 발생 시 `return None` 대신 다른 API Key로 즉시 1회 재시도 로직 추가
  - 기존: 예외 처리에서 429만 `raise`, 503 포함 나머지는 `return None`
  - 변경: `for attempt in range(2)` 루프로 최대 2회 시도. 1차 503 → `_next_key()`로 다른 키 선택 후 2차 시도. 2차도 실패 시 `None` 반환
- **변경 이유**: 로그 분석 결과 503(Gemini 서버 과부하)이 매일 10~17건 발생, 전체 에러율 20~30%에 해당. 503은 일시적 서버 과부하로 다른 키로 즉시 재시도하면 성공 가능성이 높음. 4개 키 라운드로빈 환경이므로 재시도 시 자연스럽게 다른 키가 선택됨
- **영향 범위**: `services/ai_client.py`
- **참고**: 503 에러는 Gemini 일일 쿼터(사용량)에 미포함 — 서버가 요청 처리 전 거부하는 것이므로 재시도가 쿼터를 추가 소모하지 않음. 15~21시(한국 시간)에 집중 발생하는 패턴 확인

---

### [2026-03-24] Gemini API Key 4번 추가 (라운드로빈 80 req/day 확보)
- **변경 유형**: 기능 개선
- **변경 내용**:
  - `config/settings.py`: `GEMINI_API_KEY_4` 로드 추가
  - k8s Secret: `GEMINI_API_KEY_4` 등록
  - k8s 이미지 태그: `20260324_1750`으로 업데이트
- **변경 이유**: 하루 최대 33건 요청 확인, Key 3개(60 req/day) 기준 초과 가능성 있음. Key 4개로 80 req/day 확보
- **영향 범위**: `config/settings.py`, k8s Secret

---

### [2026-04-10] .dockerignore 추가 + deployment Secret 참조 수정
- **변경 유형**: 버그 수정
- **변경 내용**:
  - `.dockerignore` 신규 생성: `.env` 파일이 Docker 이미지에 포함되던 문제 수정
  - `k8s/base/deployment.yaml`: `secretRef`에 `dev-hotdeal-bot-secret` 명시 추가
- **변경 이유**: `.dockerignore` 없어서 `.env`가 이미지에 포함되어 k8s Secret이 아닌 `.env` 기준으로 Gemini Key가 로드됨 → KEY_4 미반영. 또한 kustomize `namePrefix`는 외부 Secret 이름에 prefix를 적용하지 않아 `dev-hotdeal-bot-secret`이 Pod에 주입되지 않던 문제
- **영향 범위**: `.dockerignore`, `k8s/base/deployment.yaml`

---

### [2026-04-10] 1차/2차 알림에 쇼핑몰 + 긍정/부정/중립 분석 결과 추가
- **변경 유형**: 기능 추가
- **변경 내용**:
  - `services/notification_service.py`: 1차 알림 Embed에 쇼핑몰 필드 추가
  - `services/notification_service.py`: 2차 알림 Embed에 쇼핑몰/긍정(수+이유)/부정(수+이유)/중립(수) 필드 추가, 추천수 제거
  - `database/models.py`: `PendingAnalysis`에 `post_store` 필드 추가
  - `database/db.py`: `pending_analysis` 테이블에 `post_store` 컬럼 마이그레이션 추가, `schedule_analysis()` / `get_due_analyses()` 수정
  - `services/crawl_service.py`: `schedule_analysis()` 호출 시 `store` 전달
  - `services/analysis_service.py`: 2차 알림 `post_data`에 `store` 포함
- **변경 이유**: 어떤 쇼핑몰의 핫딜인지 1차/2차 알림 모두에서 바로 확인 가능하도록 개선. 긍정/부정/중립 분류 결과를 2차 알림에 표시하여 정보량 향상
- **영향 범위**: `services/`, `database/`

---

### [2026-03-24] google_genai/tenacity DEBUG 로그 활성화
- **변경 유형**: 기능 개선
- **변경 내용**:
  - `config/logging_config.py`: `google_genai`, `tenacity` 로거 DEBUG 레벨 설정 추가
- **변경 이유**: Gemini Studio에서 Key 3개가 각 19건씩(총 57건) 카운트되는 반면 DB 기준 요청은 23건으로 불일치 확인. SDK 내부 tenacity 자동 재시도가 실제 API 호출을 부풀리는 것으로 추정 — 재시도 발생 여부 및 횟수를 로그로 추적하기 위해 활성화
- **영향 범위**: `config/logging_config.py`
- **후속 조치**: 며칠간 데이터 수집 후 건당 실제 호출 횟수 파악, SDK 재시도 제한 여부 결정

---

### [2026-03-23] hotdeal-postgres 컨테이너 삭제
- **변경 유형**: 운영 설정 변경
- **변경 내용**:
  - `hotdeal-postgres` Docker 컨테이너 삭제 (`docker rm hotdeal-postgres`)
- **변경 이유**: 실제 봇은 `study-postgres` (`host.docker.internal:5432/studydb`)를 사용 중. `hotdeal-postgres`는 `Created` 상태로 한 번도 기동된 적 없는 미사용 컨테이너였음
- **영향 범위**: 운영 환경 (로컬 Docker). 봇 동작에 영향 없음

---

### [2026-03-18] AI 프롬프트에서 추천수 제거 + 응답 필드 확장
- **변경 유형**: 기능 개선
- **변경 내용**:
  - `services/ai_client.py` 프롬프트 수정
    - 추천수(`vote_count`) 관련 내용 완전 제거 (반응 지표, 판단 기준 문구 모두)
  - `services/ai_client.py` 응답 JSON 필드 추가
    - 기존: `{"recommendation": ..., "reason": ...}`
    - 변경: `{"recommendation": ..., "reason": ..., "positive_count": 정수, "positive_reason": "종합 이유", "negative_count": 정수, "negative_reason": "종합 이유", "neutral_count": 정수}`
    - 중립은 수만 반환, 이유 없음
  - 응답 검증 로직 강화: 기존 2개 키 → 7개 필수 키 검증으로 변경
- **변경 이유**: 추천수는 사용자 참여도가 저조하여 판단 지표로서 신뢰도가 낮음. 댓글 내 긍정/부정/중립 수와 종합 이유를 추가하여 2차 알림의 정보량 향상
- **영향 범위**: `services/ai_client.py`

---

### [2026-03-16] 삭제된 게시글 처리 정책 수정
- **변경 유형**: 버그 수정
- **변경 내용**:
  - `crawling/crawler.py` `_parse_post_detail()`: 삭제 감지 조건 정확화
    - 기존: "삭제된 게시물" 등 부정확한 문구 감지
    - 변경: `.error-page` CSS 클래스 또는 `"존재하지 않는 글입니다."` 문구 감지 (실제 Arca Live 삭제 HTML 기준)
  - `crawling/crawler.py` `fetch_post_detail()`: HTTP 404/410 응답 시 `deleted=True` 반환 추가 (폴백)
  - `services/analysis_service.py`: 삭제 감지 시 AI 요청 없이 `done` 처리, 삭제 알림 전송 제거
  - `services/notification_service.py`: `send_deleted_post_notice()` 메서드 제거
- **변경 이유**: Arca Live는 삭제된 게시글에도 HTTP 200을 반환하며 본문에 "존재하지 않는 글입니다." 텍스트를 포함하는 구조. 기존 404 HTTP 감지로는 실제 삭제 게시글이 탐지되지 않았음
- **영향 범위**: `crawling/crawler.py`, `services/analysis_service.py`, `services/notification_service.py`
- **삭제 처리 정책**: 삭제 감지 시 AI 미호출, 사용자 DM 미전송, status → done 으로 조용히 종료

---

### [2026-03-16] AI 프롬프트 판단 우선순위 변경 (댓글 수 1순위, 추천수 2순위)
- **변경 유형**: 기능 개선
- **변경 내용**:
  - `services/ai_client.py` 프롬프트 수정
    - 반응 지표 순서: 추천수 → 댓글수 / 댓글수(1순위) → 추천수(2순위)로 변경
    - 판단 기준 문구: "추천수와 댓글의 분위기" → "댓글의 분위기를 1순위로, 추천수를 2순위로"로 명시
- **변경 이유**: 추천수보다 댓글 내용이 구매 의사 판단에 더 직접적인 정보를 담고 있음
- **영향 범위**: `services/ai_client.py`

---

### [2026-03-16] !사용법 명령어 추가
- **변경 유형**: 기능 추가
- **변경 내용**:
  - `bot.py`: `!사용법` 명령어 추가 — 키워드/카테고리/기타 섹션으로 나뉜 Embed 응답 출력
- **변경 이유**: 신규 사용자가 봇 명령어를 쉽게 파악할 수 있도록 사용법 안내 명령어 추가
- **영향 범위**: `bot.py`

---

### [2026-03-16] README 봇 명령어 섹션 개편
- **변경 유형**: 문서 개선
- **변경 내용**:
  - 봇 명령어를 시스템 / 키워드 / 카테고리 그룹으로 분리
  - `!핫딜`, `/핫딜추가` 누락 명령어 추가 후 구현 예정 항목 제거
  - `.env.example`: `GEMINI_API_KEY` → `GEMINI_API_KEY_1,2,3` 구조로 업데이트
  - `docs/api_docs.md` 신규 생성 (Discord 명령어 API, DB API, Service API, AI Client API)
- **영향 범위**: `README.md`, `.env.example`, `docs/api_docs.md`

---

### [2026-03-15] Gemini 프롬프트 개선 - 커뮤니티 반응 기반 분석으로 변경
- **변경 유형**: 기능 개선
- **변경 내용**:
  - `services/ai_client.py` Gemini 프롬프트 수정
    - 페르소나 변경: `온라인 핫딜 전문가` → `커뮤니티 반응 분석가`
    - 제품 사전 지식 사용 금지 명시 ("제품에 대한 사전 지식은 사용하지 마세요")
    - 가격 항목 제거 (빈 값으로 전달되고 있었으며 지식 기반 판단 유발 가능성 있음)
    - 판단 기준 명시: 댓글 긍정/부정/중립 비율, 구매 후기, 가격 반응 등
  - 이미지 태그: `hotdeal-bot:20260315_2353`
- **변경 이유**: Gemini의 모델 학습 데이터(과거 지식) 의존을 줄이고, 실시간 커뮤니티 반응(추천수·댓글)만으로 판단하도록 개선
- **영향 범위**: `services/ai_client.py`

---

### [2026-03-15] Gemini API Key 로드밸런싱 구현 (3개 Key 라운드로빈)
- **변경 유형**: 기능 추가
- **변경 내용**:
  - `config/settings.py`: `GEMINI_API_KEY` 단일 → `GEMINI_API_KEYS` 리스트로 변경 (`KEY_1,2,3` 로드, 없으면 단일 `GEMINI_API_KEY` 폴백)
  - `services/ai_client.py`: `_next_key()` 라운드로빈 구현, `gemini-2.5-flash-lite` → `gemini-2.5-flash` 복원
  - `bot.py`, `services/crawl_service.py`: `GEMINI_API_KEYS` 리스트 기준으로 체크, 로그에 Key 개수 표시
  - `k8s/overlays/dev/kustomization.yaml`: 이미지 태그 `20260315_1930`으로 업데이트
- **변경 이유**: Gemini 무료 tier 일일 한도가 Key당 20 req/day로 확인됨. 하루 핫딜 수집량(약 25건)이 한도 초과. Key 3개 라운드로빈으로 60 req/day 확보
- **영향 범위**: `config/`, `services/ai_client.py`, `bot.py`, `services/crawl_service.py`, `k8s/`
- **호출 순서**: KEY_1 → KEY_2 → KEY_3 → KEY_1 순환

---

### [2026-03-15] AI 모델 gemini-2.5-flash → gemini-2.5-flash-lite 변경 (롤백됨)
- **변경 유형**: 설정 변경
- **변경 내용**:
  - `services/ai_client.py`: 모델명 `gemini-2.5-flash` → `gemini-2.5-flash-lite`
  - `k8s/overlays/dev/kustomization.yaml`: 이미지 태그 `20260315_1920`으로 업데이트
- **변경 이유**: gemini-2.5-flash-lite는 경량 모델로 무료 사용량 한도가 더 높음. 핫딜 추천/비추천 판단 품질은 동일하게 충분함 확인
- **영향 범위**: `services/ai_client.py`

---

### [2026-03-15] Gemini 429 사용량 제한 시 재시도 누락 버그 수정
- **변경 유형**: 버그 수정
- **변경 내용**:
  - `services/ai_client.py`: `ClientError` 중 `status_code == 429`인 경우 `return None` 대신 `raise`로 상위 전파
- **변경 이유**: 429(사용량 제한)는 일시적 오류임에도 `return None`으로 처리되어 `_process()`가 정상 완료 → `status='done'`으로 확정되어 재시도 로직이 전혀 작동하지 않는 문제 발견
- **영향 범위**: `services/ai_client.py`
- **참고**: 429 외 오류(응답 형식 불일치 등)는 기존대로 `return None` 유지. Gemini 사용량은 태평양 표준시(PST) 자정 기준 리셋

---

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
