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
