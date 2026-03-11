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
