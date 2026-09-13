# 기획 산출물 — 애플 리퍼비쉬 MacBook Pro 감시 (일회성 개인 알림)

작성일: 2026-09-13

## 1. 배경 및 목적

- 봇 운영자가 애플 공식 리퍼비쉬 스토어(한국)에서 MacBook Pro를 **1대 구매**하려 한다.
- 원하는 사양의 재고는 드물게, 예고 없이 올라오므로 사람이 계속 새로고침하기 어렵다.
- 이미 24시간 기동 중인 핫딜 봇에 **감시 태스크**를 가볍게 붙여, 조건에 맞는 재고가 새로 뜨면 Discord DM으로 즉시 알린다.
- 수신자 관리는 **기존 키워드 기능을 재활용**한다. 트리거 키워드(기본 `애플리퍼`)를 `!키워드 추가`로 등록한 사용자에게만 보내고, 등록자가 없으면 크롤링도 하지 않는다.
- 구매가 끝나면 `!키워드 삭제 애플리퍼`로 끈다. Secret 수정이나 파드 재시작이 필요 없다.
- 사양 조건은 코드 필터가 처리한다. 기존 키워드 매칭 파이프라인에 태우지 않는 이유는 (1) 제목에 메모리·용량이 없어 조건을 키워드로 표현할 수 없고, (2) `*`·`맥북` 등록자 등 다른 사용자에게 알림이 새고, (3) 댓글 없는 페이지에 AI 2차 분석이 걸려 Gemini 쿼터를 낭비하기 때문이다.

## 2. 대상 페이지

| 항목 | 값 |
|------|------|
| URL | `https://www.apple.com/kr/shop/refurbished/mac` |
| 렌더링 | 서버 사이드 HTML. JS 없이 상품 목록 확보 가능 |
| 데이터 위치 | 스크립트 내 `"tiles":[...]` JSON (1순위), `.rf-refurb-category-grid-no-js` HTML (폴백) |
| 타일 필드 | `partNumber`, `title`, `price.currentPrice.raw_amount`, `productDetailsUrl`, `filters.dimensions.{refurbClearModel, dimensionScreensize, dimensionCapacity, tsMemorySize}` |
| robots.txt | 리퍼비쉬 경로 차단 없음 |
| 참고 | `/mac/macbook-pro`, `/mac/macbook-air` 등 하위 URL은 `/mac`으로 리다이렉트되므로 `/mac` 하나만 감시 |

## 3. 알림 조건 (요구사항)

| 조건 | 값 | 판별 근거 |
|------|------|-----------|
| 모델 | MacBook Pro | `refurbClearModel == "macbookpro"` |
| 화면 | 14인치 | `dimensionScreensize == "14inch"` |
| 메모리 | 64GB 이상 | `tsMemorySize` (예: `"64gb"`) |
| 저장용량 | 1TB 이상 | `dimensionCapacity` (예: `"1tb"`, `"2tb"`) |
| 칩 | M3, M4, M5 계열 전부 (Pro/Max 포함) | 제목에서 `M3`/`M4`/`M5` 정규식 추출 |
| 가격 상한 | 없음 (선택 설정 가능) | `price.currentPrice.raw_amount` |

- 필터 값이 **없는** 항목(예: 메모리 정보 누락)은 **알림을 보내되 "정보 없음"으로 표시**한다. 일회성 구매 알림이므로 놓치는 쪽보다 한 번 더 확인하는 쪽이 낫다.
- 조건은 전부 환경변수로 덮어쓸 수 있으며 기본값이 위 요구사항과 같다.

## 4. 동작 흐름

```
10분마다
  └─ 트리거 키워드('애플리퍼') 등록자 조회 (keywords 테이블) → 0명이면 크롤링 없이 종료
  └─ 페이지 fetch (재시도 3회)
  └─ tiles JSON 파싱 → 상품 목록
       └─ 파싱 결과 0개 → 경고 로그, 스냅샷 건드리지 않음 (오탐 방지)
  └─ DB 스냅샷(apple_refurb_snapshot)과 비교 → 새 부품번호 추출
       └─ 첫 실행(crawl_state에 apple_refurb 없음) → 알림 없이 스냅샷만 저장
  └─ 새 항목 중 조건 일치 → 등록자 전원에게 DM (실패 시 채널 폴백)
  └─ 스냅샷 갱신 (사라진 재고 삭제, 현재 재고 upsert)
```

- 재고가 사라졌다가 다시 올라오면 스냅샷에 없으므로 **다시 새 항목으로 인식**되어 알림이 온다. (리퍼는 품절/재입고가 반복되므로 의도된 동작)
- 기존 핫딜 파이프라인(키워드 매칭, hotdeals 저장, AI 2차 분석)은 전혀 거치지 않는다.

## 5. 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `APPLE_REFURB_TRIGGER_KEYWORD` | `애플리퍼` | 이 키워드를 `!키워드 추가`로 등록한 사용자가 수신자. **등록자 없으면 크롤링도 안 함** |
| `APPLE_REFURB_INTERVAL_MINUTES` | `10` | 감시 주기(분) |
| `APPLE_REFURB_MODEL` | `macbookpro` | 모델 필터 |
| `APPLE_REFURB_SCREEN` | `14inch` | 화면 필터 |
| `APPLE_REFURB_MIN_MEMORY_GB` | `64` | 최소 메모리 |
| `APPLE_REFURB_MIN_STORAGE_GB` | `1024` | 최소 저장용량(GB) |
| `APPLE_REFURB_CHIPS` | `M3,M4,M5` | 허용 칩 세대(쉼표 구분) |
| `APPLE_REFURB_MAX_PRICE` | (없음) | 가격 상한(원). 비우면 제한 없음 |

## 6. 산출물

| 구분 | 파일 |
|------|------|
| 설정 | `config/settings.py` |
| DB | `database/db.py` — `apple_refurb_snapshot` 테이블, `get_refurb_snapshot`, `replace_refurb_snapshot` |
| 서비스 | `services/apple_refurb_watcher.py` |
| 알림 | `services/notification_service.py` — `send_refurb_alert` |
| 진입점 | `bot.py` — `apple_refurb_task` |
| 테스트 | `tests/unit/test_apple_refurb_watcher.py`, `tests/integration/test_database.py` |
| 문서 | README, docs/change_log.md, docs/api_docs.md, .env.example, k8s configmap |

## 7. 켜기 / 끄기

| 동작 | 방법 |
|------|------|
| 켜기 | 디스코드에서 `!키워드 추가 애플리퍼` |
| 끄기 | 디스코드에서 `!키워드 삭제 애플리퍼` |
| 완전 제거 | 코드 삭제 + `apple_refurb_snapshot` 테이블 DROP (선택) |

- 등록자가 0명이면 태스크는 매 회 즉시 반환하므로 애플 서버에 요청도 가지 않는다.
- `애플리퍼`는 아카라이브 제목에 나올 일이 없어 일반 핫딜 알림과 섞이지 않는다.
