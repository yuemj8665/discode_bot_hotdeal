# 에러 이벤트 기록

프로젝트에서 발생한 에러와 해결 방법을 기록합니다.

---

## 에러 템플릿

```
### [YYYY-MM-DD] 에러 제목
- **에러 메시지**:
- **발생 상황**:
- **원인**:
- **해결 방법**:
- **참고**:
```

---

## 기록된 에러

### [2026-03-15] AttributeError: Settings has no attribute 'ANTHROPIC_API_KEY'
- **에러 메시지**: `AttributeError: type object 'Settings' has no attribute 'ANTHROPIC_API_KEY'`
- **발생 상황**: Gemini 교체 배포 후 `on_ready` 및 `analysis_task` 실행 시 봇 크래시
- **원인**: `config/settings.py`에서 `ANTHROPIC_API_KEY`를 `GEMINI_API_KEY`로 변경했으나 `bot.py`(2곳), `services/crawl_service.py`(1곳)에 기존 속성명이 잔존
- **해결 방법**: 3곳 모두 `Settings.ANTHROPIC_API_KEY` → `Settings.GEMINI_API_KEY`로 교체
- **참고**: SDK 교체 시 관련 설정 참조 전체를 `grep -rn`으로 확인하는 습관 필요

---

### [2026-03-15] Gemini 모델 404 NOT_FOUND (gemini-1.5-flash)
- **에러 메시지**: `404 NOT_FOUND: models/gemini-1.5-flash is not found for API version v1beta`
- **발생 상황**: `ai_client.py`에서 `gemini-1.5-flash` 모델로 호출 시 발생
- **원인**: `gemini-1.5-flash`는 해당 API 버전에서 지원 종료됨
- **해결 방법**: `gemini-2.5-flash`로 모델명 변경 (계정에서 사용 가능한 모델은 `client.models.list()`로 확인)
- **참고**: `gemini-2.0-flash`, `gemini-2.0-flash-lite`는 해당 계정의 free tier quota가 `limit: 0`으로 설정되어 사용 불가. `gemini-2.5-flash`만 정상 동작 확인

---

### [2026-03-15] Gemini 429 RESOURCE_EXHAUSTED (free tier limit: 0)
- **에러 메시지**: `429 RESOURCE_EXHAUSTED: Quota exceeded, limit: 0, model: gemini-2.0-flash`
- **발생 상황**: `gemini-2.0-flash` 및 `gemini-2.0-flash-lite` 호출 시 발생
- **원인**: Google AI Studio에서 발급한 Key임에도 특정 모델의 free tier 할당량이 0으로 설정된 계정 상태
- **해결 방법**: `gemini-2.5-flash` 모델 사용으로 우회 (해당 모델은 정상 동작 확인)
- **참고**: 모델별 quota는 `https://ai.dev/rate-limit`에서 확인 가능. `limit: 0`은 사용량 초과가 아닌 할당량 미부여 상태

---

### [2026-03-15] 봇 명령어 응답 중복 (두 번씩 응답)
- **에러 메시지**: 직접적인 에러 없음 (`!ping` 등 명령어에 응답이 2회 전송됨)
- **발생 상황**: `!ping` 입력 시 동일한 내용의 응답이 연속으로 두 번 수신
- **원인**: k8s Pod(ArgoCD 배포)와 로컬 PC의 docker-compose 컨테이너가 동일한 Discord 토큰으로 동시에 실행 중. 두 인스턴스 모두 같은 메시지를 수신하고 각각 응답 전송
- **해결 방법**: `docker ps | grep hotdeal`로 실행 중인 컨테이너 목록 확인 후, 로컬 컨테이너 `docker compose -f docker-compose.yaml down`으로 중지
- **참고**: k8s 환경을 운영 기준으로 결정. 로컬에서 개발/테스트 시 주의 필요. 동일 토큰으로 두 인스턴스를 동시에 실행하면 반드시 이 현상 발생

---

### [2026-03-15] ArgoCD 자동 배포 미반응
- **에러 메시지**: ArgoCD UI에서 변경 감지 없음
- **발생 상황**: 소스코드(`ADD Category command`) 커밋 후 push했으나 ArgoCD가 재배포하지 않음
- **원인**: ArgoCD는 `k8s/overlays/dev` 경로의 매니페스트 변경만 감지함. 소스코드만 바꿨을 뿐 `kustomization.yaml`의 이미지 태그(`newTag`)가 그대로여서 배포할 변경사항 없음으로 판단
- **해결 방법**: 새 이미지 빌드 후 `k8s/overlays/dev/kustomization.yaml`의 `newTag` 값을 새 태그로 수정하여 push
- **참고**: ArgoCD 기본 폴링 주기는 3분. UI에서 수동 Refresh로 즉시 확인 가능

---

### [2026-03-11] _filter_by_url 버그 — 오래된 게시글까지 새것으로 처리
- **에러 메시지**: 테스트 실패 `AssertionError: assert '98' not in ['100', '98']`
- **발생 상황**: `CrawlService._filter_by_url()`에서 마지막 URL 발견 후에도 이후 게시글을 계속 수집
- **원인**: 마지막 URL 매칭 시 `continue`로 건너뛰기만 하고 루프를 종료하지 않아, 이전(오래된) 게시글까지 `new_posts`에 포함됨
- **해결 방법**: `continue` → `break` 로 변경 (`crawl_service.py`)
- **참고**: 유닛 테스트(`test_returns_posts_before_last_url`) 작성으로 최초 발견

---

### [2026-03-11] save_posts 버그 — 매 크롤링마다 전체 게시글 DB write 반복
- **에러 메시지**: 직접적인 에러 없음 (기능은 동작하지만 불필요한 쿼리 발생)
- **발생 상황**: `CrawlService.run()`에서 `new_posts` 필터링 후 `all_posts` 전체를 저장
- **원인**: `save_posts(all_posts)` 로 잘못 호출 — 매 크롤링(1분)마다 페이지 전체(약 20~30개) INSERT 시도
- **해결 방법**: `save_posts(all_posts)` → `save_posts(new_posts)` 로 변경 (`crawl_service.py`)
- **참고**: `ON CONFLICT DO NOTHING` 덕분에 데이터 오염은 없었으나 DB 부하 누적

---

### [2026-03-11] pytest 통합 테스트 — RuntimeError: Task attached to a different loop
- **에러 메시지**: `RuntimeError: Task got Future attached to a different loop`
- **발생 상황**: 통합 테스트 실행 시 `scope="module"` DB 픽스처와 각 테스트의 개별 이벤트 루프 충돌
- **원인**: `pytest-asyncio`에서 `scope="module"` 비동기 픽스처가 테스트별 이벤트 루프와 다른 루프에 바인딩됨
- **해결 방법**: `db` 픽스처 scope를 `"module"` → `"function"`으로 변경, `event_loop` 커스텀 픽스처 제거
- **참고**: 테스트마다 DB 연결을 새로 생성/종료하는 방식으로 변경

---

### [2026-03-11] test_update_with_datetime 테스트 실패
- **에러 메시지**: `AssertionError: assert None == datetime.datetime(2026, 3, 11, 10, 0)`
- **발생 상황**: `update_last_post_id()` 호출 시 `post_url` 없이 `post_datetime`만 전달
- **원인**: `update_last_post_id()` 내부 분기 로직상 `post_url`이 없으면 `post_datetime`도 저장하지 않음 (의도된 동작)
- **해결 방법**: 테스트 코드에서 `post_url`을 함께 전달하도록 수정
- **참고**: 코드 버그가 아닌 테스트 작성 오류
