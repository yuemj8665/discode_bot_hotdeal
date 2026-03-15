# API 문서

핫딜 봇의 Discord 명령어 및 내부 서비스 API를 정리합니다.

---

## 목차

1. [Discord 명령어 API](#1-discord-명령어-api)
2. [Database API](#2-database-api)
3. [Service API](#3-service-api)
4. [AI Client API](#4-ai-client-api)

---

## 1. Discord 명령어 API

### 공통 사항

- **접두사**: `!` (기본값, `COMMAND_PREFIX` 환경변수로 변경 가능)
- **응답 형식**: Discord Embed
- **응답 색상 규칙**:
  - `0x00ff00` (초록) — 성공
  - `0xffaa00` (주황) — 경고 (중복, 없음)
  - `0x5865F2` (보라) — 조회
  - `0xFF0000` (빨강) — 에러

---

### 1-1. 키워드 명령어

**파일**: `commands/keyword.py`

#### `!키워드 추가 [단어]`

키워드를 등록합니다. 등록된 키워드가 핫딜 제목에 포함되면 DM 알림이 전송됩니다.

| 항목 | 내용 |
|------|------|
| 사용법 | `!키워드 추가 노트북` |
| 특수 키워드 | `*` 입력 시 모든 핫딜 알림 (와일드카드) |
| 성공 응답 | `✅ 키워드 추가 완료` Embed |
| 중복 응답 | `⚠️ 키워드 중복` Embed |
| 오류 응답 | `❌ 키워드 추가 중 오류가 발생했습니다` |

#### `!키워드 삭제 [단어]`

등록된 키워드를 삭제합니다.

| 항목 | 내용 |
|------|------|
| 사용법 | `!키워드 삭제 노트북` |
| 성공 응답 | `✅ 키워드 삭제 완료` Embed |
| 없음 응답 | `⚠️ 키워드 없음` Embed |

#### `!키워드 목록`

등록된 키워드 전체 목록을 조회합니다.

| 항목 | 내용 |
|------|------|
| 사용법 | `!키워드 목록` |
| 응답 | 키워드 목록 Embed (없으면 안내 메시지) |
| Footer | `총 N개의 키워드` |

---

### 1-2. 카테고리 명령어

**파일**: `commands/category.py`

#### 구독 가능한 카테고리 목록

`식품` · `생활용품` · `전자제품` · `PC/하드웨어` · `SW/게임` · `의류` · `화장품` · `상품권/쿠폰` · `임박` · `응모` · `기타`

#### `!카테고리 추가 [카테고리명]`

카테고리를 구독합니다. 해당 카테고리 핫딜 발생 시 알림이 전송됩니다.

| 항목 | 내용 |
|------|------|
| 사용법 | `!카테고리 추가 식품` |
| 유효성 검사 | 위 목록에 없는 카테고리명 입력 시 오류 |
| 성공 응답 | `✅ 카테고리 구독 추가 완료` Embed |
| 중복 응답 | `⚠️ 카테고리 중복` Embed |

#### `!카테고리 삭제 [카테고리명]`

구독 중인 카테고리를 삭제합니다.

| 항목 | 내용 |
|------|------|
| 사용법 | `!카테고리 삭제 식품` |
| 성공 응답 | `✅ 카테고리 구독 삭제 완료` Embed |
| 없음 응답 | `⚠️ 카테고리 없음` Embed |

#### `!카테고리 목록`

구독 중인 카테고리 전체 목록을 조회합니다.

| 항목 | 내용 |
|------|------|
| 사용법 | `!카테고리 목록` |
| 응답 | 카테고리 목록 Embed (없으면 안내 메시지) |

---

### 1-3. 핫딜 명령어

**파일**: `commands/hotdeal.py`

#### `/핫딜` (슬래시 명령어)

최근 핫딜 목록을 조회합니다. (구현 예정)

| 항목 | 내용 |
|------|------|
| 타입 | 슬래시 명령어 |
| 응답 방식 | `ephemeral=True` (본인에게만 표시) |

---

## 2. Database API

**파일**: `database/db.py`
**클래스**: `Database`

모든 메서드는 `async`입니다. 내부적으로 `asyncpg` 커넥션 풀을 사용합니다.

---

### 2-1. 연결 관리

#### `connect()`
```python
await db.connect()
```
DB 연결 및 테이블 초기화. 봇 시작 시 `on_ready`에서 호출합니다.

#### `close()`
```python
await db.close()
```
커넥션 풀 종료.

---

### 2-2. 핫딜 (hotdeals)

#### `add_hotdeal(hotdeal: Hotdeal) -> bool`
핫딜을 저장합니다. URL 중복 시 무시 (`ON CONFLICT DO NOTHING`).

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `hotdeal` | `Hotdeal` | 저장할 핫딜 데이터 |
| 반환 | `bool` | `True`: 신규 저장, `False`: 중복 |

#### `get_hotdeals(limit: int = 10) -> List[Hotdeal]`
최근 핫딜 목록을 조회합니다.

#### `get_hotdeal_by_url(url: str) -> Optional[Hotdeal]`
URL로 핫딜 단건 조회.

#### `cleanup_old_hotdeals(hours: int = 24) -> int`
N시간 이상 된 핫딜을 삭제합니다.

| 반환 | `int` | 삭제된 건수 |

---

### 2-3. 사용자 (users)

#### `add_user(user_id: int) -> bool`
사용자를 등록합니다. 이미 존재하면 무시.

#### `get_user(user_id: int) -> Optional[User]`
사용자 단건 조회.

#### `delete_user(user_id: int) -> bool`
사용자 삭제 (연관 키워드, 카테고리 CASCADE 삭제).

---

### 2-4. 키워드 (keywords)

#### `add_keyword(user_id: int, keyword: str) -> bool`
키워드 등록. 사용자가 없으면 자동 생성.

| 반환 | `bool` | `True`: 신규, `False`: 중복 |

#### `get_keywords(user_id: int) -> List[Keyword]`
사용자의 키워드 목록 조회.

#### `delete_keyword(user_id: int, keyword: str) -> bool`
키워드 삭제.

| 반환 | `bool` | `True`: 삭제 성공, `False`: 없음 |

#### `get_all_keywords() -> List[str]`
전체 사용자의 키워드 중복 없이 조회 (크롤링 시 필터링 최적화용).

#### `get_users_by_keyword(keyword: str) -> List[int]`
특정 키워드를 가진 사용자 ID 목록 반환.

---

### 2-5. 카테고리 (user_categories)

#### `add_category(user_id: int, category: str) -> bool`
카테고리 구독 등록.

#### `get_categories(user_id: int) -> List[Category]`
사용자의 카테고리 구독 목록.

#### `delete_category(user_id: int, category: str) -> bool`
카테고리 구독 삭제.

#### `get_all_categories() -> List[str]`
전체 구독 중인 카테고리 중복 없이 반환.

#### `get_users_by_category(category: str) -> List[int]`
특정 카테고리를 구독한 사용자 ID 목록 반환.

---

### 2-6. 크롤링 상태 (crawl_state)

#### `get_last_post_id(crawler_name: str) -> Optional[str]`
마지막으로 처리한 게시글 ID 조회.

#### `get_last_post_url(crawler_name: str) -> Optional[str]`
마지막으로 처리한 게시글 URL 조회.

#### `get_last_post_datetime(crawler_name: str) -> Optional[datetime]`
마지막으로 처리한 게시글 작성 시간 조회.

#### `update_last_post_id(crawler_name, post_id, post_url=None, post_datetime=None) -> bool`
크롤링 상태 업데이트. datetime → url → id 우선순위로 저장.

---

### 2-7. 알림 채널 (notification_channels)

#### `set_notification_channel(guild_id: int, channel_id: int) -> bool`
서버별 알림 채널 설정.

#### `get_notification_channel(guild_id: int) -> Optional[int]`
서버별 알림 채널 ID 조회.

---

### 2-8. AI 분석 (pending_analysis)

#### `schedule_analysis(post_url: str, post_title: str, scheduled_at: datetime) -> bool`
AI 분석 예약 등록. URL 중복 시 무시.

#### `get_due_analyses() -> List[PendingAnalysis]`
`scheduled_at <= now`이고 `status='pending'`인 항목 조회.

#### `update_analysis_status(analysis_id: int, status: str) -> bool`
분석 상태 업데이트.

| status 값 | 설명 |
|-----------|------|
| `pending` | 대기 중 |
| `processing` | 처리 중 (중복 방지용) |
| `done` | 완료 |
| `failed` | 최종 실패 (재시도 초과) |

#### `reschedule_failed_analysis(analysis_id: int, retry_after_minutes: int = 5) -> bool`
실패한 항목을 N분 후 재시도 예약.
- `status` → `pending`
- `scheduled_at` → `now + N분`
- `retry_count` → `+1`

#### `cleanup_old_analyses(days: int = 7) -> int`
N일 이상 된 분석 항목 삭제.

---

### 2-9. 알림 이력 (notification_history)

#### `record_notification(post_url: str, user_id: int) -> bool`
1차 알림 수신 기록. (중복 무시)

#### `get_notified_users(post_url: str) -> List[int]`
특정 게시글의 1차 알림 수신자 목록 반환. AI 2차 알림 대상 조회에 사용.

---

## 3. Service API

### 3-1. CrawlService

**파일**: `services/crawl_service.py`

#### `run() -> None`
크롤링 파이프라인 실행. `bot.py`의 `crawl_task`에서 1분마다 호출.

```
fetch() → filter() → save() → notify()
```

| 단계 | 설명 |
|------|------|
| fetch | Arca Live 핫딜 페이지 크롤링 |
| filter | 마지막 게시글 이후 신규 항목만 추출 (datetime → url → id 폴백) |
| save | DB에 신규 핫딜 저장 |
| notify | 키워드·카테고리 매칭 사용자에게 알림 전송, AI 분석 예약 |

---

### 3-2. NotificationService

**파일**: `services/notification_service.py`

#### `send_notifications(user_id: int, post_data: dict) -> bool`
1차 핫딜 알림 전송. DM 우선, 실패 시 서버 채널 폴백.

| 파라미터 | 설명 |
|----------|------|
| `user_id` | Discord 사용자 ID |
| `post_data` | `title`, `price`, `full_url`, `category`, `matched_keywords` 포함 dict |

#### `send_analysis_result(user_id: int, post_data: dict, ai_result: Optional[dict]) -> None`
AI 2차 분석 알림 전송.

| 파라미터 | 설명 |
|----------|------|
| `ai_result` | `{"recommendation": "추천"/"비추천", "reason": "..."}` 또는 `None` |
| `ai_result=None` | AI 결과 없이 추천수·댓글수 통계만 Embed으로 전송 |

**Embed 색상 규칙**:
- 추천 → `0x00ff00` (초록)
- 비추천 → `0xff0000` (빨강)
- AI 결과 없음 → `0x808080` (회색)

---

### 3-3. AnalysisService

**파일**: `services/analysis_service.py`

#### `run() -> int`
`scheduled_at`이 지난 `pending` 항목을 일괄 처리.

| 반환 | `int` | 처리 완료된 항목 수 |

**재시도 정책**:
- 처리 중 예외 발생 시 `retry_count < 3` → 5분 후 재시도 예약
- `retry_count >= 3` → `failed` 확정

---

## 4. AI Client API

**파일**: `services/ai_client.py`
**클래스**: `AIClient`

### `__init__()`
`Settings.GEMINI_API_KEYS` 리스트를 로드. Key가 없으면 `enabled=False`.

### `analyze_hotdeal(...) -> Optional[dict]`

```python
result = await ai_client.analyze_hotdeal(
    title="삼성 갤럭시 버즈3 프로 20% 할인",
    price="89,000원",
    vote_count=85,
    comment_count=42,
    comments=["역대급 최저가", "바로 샀어요"]
)
# 반환: {"recommendation": "추천", "reason": "..."}
```

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `title` | `str` | 게시글 제목 |
| `price` | `str` | 가격 (없으면 빈 문자열) |
| `vote_count` | `int` | 추천수 |
| `comment_count` | `int` | 댓글 수 |
| `comments` | `list` | 댓글 목록 (최대 20개 사용) |

| 반환값 | 조건 |
|--------|------|
| `{"recommendation": "추천"/"비추천", "reason": "..."}` | 정상 |
| `None` | Key 미설정 또는 오류 |
| `raise ClientError(429)` | 사용량 초과 → `AnalysisService`에서 재시도 처리 |

**사용 모델**: `gemini-2.5-flash`
**로드밸런싱**: `KEY_1 → KEY_2 → KEY_3 → KEY_1` 라운드로빈
**사용량 한도**: Key 1개당 20 req/day (PST 자정 리셋)

---

*최종 업데이트: 2026-03-15*
