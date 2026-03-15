# 핫딜 봇 (Hotdeal Bot)

Discord에서 Arca Live 핫딜 게시판을 자동 모니터링하고 키워드 · 카테고리 매칭 알림을 제공하는 봇입니다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [데이터베이스 구조](#3-데이터베이스-구조)
4. [사용 기술 및 선택 이유](#4-사용-기술-및-선택-이유)
5. [설치 및 실행 방법](#5-설치-및-실행-방법)
6. [에러 모음](#6-에러-모음)

---

## 1. 프로젝트 개요

### 주요 기능

- **핫딜 크롤링**: Arca Live 핫딜 게시판을 1분마다 자동 크롤링
- **키워드 알림**: 사용자가 등록한 키워드와 매칭되는 핫딜 발견 시 Discord DM 또는 채널 알림 전송
- **카테고리 알림**: 식품 · 전자제품 등 카테고리 구독 시 해당 카테고리 핫딜 알림 전송 (키워드와 OR 조건)
- **키워드 관리**: 사용자별 키워드 추가 / 삭제 / 목록 조회
- **카테고리 관리**: 사용자별 카테고리 구독 추가 / 삭제 / 목록 조회
- **중복 방지**: 마지막 게시글 datetime / URL / ID 기반 3단계 폴백으로 중복 알림 방지
- **데이터 정리**: 24시간 이상 된 핫딜 데이터 자동 삭제
- **AI 분석 2차 알림** *(선택)*: `GEMINI_API_KEY` 설정 시, 1차 알림 3시간 후 추천수 · 댓글을 재크롤링하여 Gemini 2.5 Flash가 추천/비추천 판단 및 이유를 2차 알림으로 전송. 실패 시 5분 후 자동 재시도 (최대 3회)

### 봇 명령어

> 기본 접두사: `!` (`COMMAND_PREFIX` 환경변수로 변경 가능)

#### 시스템

| 명령어 | 설명 |
|--------|------|
| `!ping` | 봇 응답 속도 확인 |
| `!정보` | 봇 정보 및 버전 확인 |

#### 키워드 관리

| 명령어 | 설명 | 비고 |
|--------|------|------|
| `!키워드 추가 [단어]` | 알림 키워드 등록 | `*` 입력 시 모든 핫딜 수신 (와일드카드) |
| `!키워드 삭제 [단어]` | 등록된 키워드 삭제 | |
| `!키워드 목록` | 등록된 키워드 전체 조회 | |

#### 카테고리 구독

| 명령어 | 설명 |
|--------|------|
| `!카테고리 추가 [카테고리명]` | 카테고리 구독 추가 |
| `!카테고리 삭제 [카테고리명]` | 카테고리 구독 삭제 |
| `!카테고리 목록` | 구독 중인 카테고리 전체 조회 |


#### AI 2차 알림 (선택 기능)

별도의 봇 명령어는 없습니다. **환경변수 설정만으로 활성화/비활성화**합니다.

| 설정 방법 | 내용 |
|-----------|------|
| **활성화** | `.env` 또는 k8s Secret에 `GEMINI_API_KEY_1` (최소 1개) 설정 |
| **비활성화** | `GEMINI_API_KEY_1,2,3` 모두 미설정 (기본값) |

활성화 시 동작:
1. 핫딜 1차 알림 수신 후 **3시간 뒤** 자동으로 Gemini AI 분석 실행
2. 해당 게시글의 최신 추천수 · 댓글을 재크롤링하여 **추천 / 비추천** 판단
3. 1차 알림을 받은 사용자에게 DM으로 2차 분석 결과 전송
4. 실패 시 5분 후 자동 재시도 (최대 3회)

### 구독 가능한 카테고리

`식품` · `생활용품` · `전자제품` · `PC/하드웨어` · `SW/게임` · `의류` · `화장품` · `상품권/쿠폰` · `임박` · `응모` · `기타`

### 알림 동작 방식

1. 키워드 또는 카테고리 중 하나라도 매칭되면 알림 발송 (OR 조건)
2. DM 전송 우선 → DM 불가 시 서버 지정 채널 or `general` 채널로 폴백
3. `*` 키워드 등록 시 모든 핫딜에 매칭 (와일드카드)
4. *(선택)* 1차 알림 3시간 후 Gemini AI가 추천수·댓글 기반으로 구매 추천 여부를 2차 알림으로 전송 (실패 시 5분 후 자동 재시도, 최대 3회)

---

## 2. 프로젝트 구조

```
discode_bot_hotdeal/
├── bot.py                    # 봇 메인 진입점
├── requirements.txt          # Python 의존성
├── Dockerfile                # Docker 이미지 빌드 파일
├── docker-compose.yml        # 로컬 개발용 Docker Compose
├── docker-compose.yaml       # 홈 서버 배포용 Docker Compose
├── .env.example              # 환경 변수 예시 파일
├── config/                   # 설정 모듈
│   ├── settings.py           # 환경 변수 관리
│   └── logging_config.py     # 로깅 설정
├── commands/                 # 봇 명령어 모듈
│   ├── hotdeal.py            # 핫딜 조회 명령어
│   ├── keyword.py            # 키워드 관리 명령어
│   └── category.py           # 카테고리 구독 명령어
├── crawling/                 # 크롤링 모듈
│   ├── base.py               # 기본 크롤러 클래스
│   └── crawler.py            # Arca Live 핫딜 크롤러 구현
├── database/                 # 데이터베이스 모듈
│   ├── models.py             # 데이터 모델 (Hotdeal, User, Keyword, Category 등)
│   └── db.py                 # 비동기 PostgreSQL 연결 및 쿼리
├── services/                 # 서비스 레이어
│   ├── crawl_service.py      # 크롤링 파이프라인 (fetch → filter → save → notify)
│   ├── notification_service.py # Discord 알림 전송
│   ├── analysis_service.py   # AI 분석 2차 알림 서비스
│   └── ai_client.py          # Google Gemini API 클라이언트
├── utils/                    # 유틸리티 모듈
│   └── helpers.py
├── tests/                    # 자동화 테스트
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_crawler.py
│   │   └── test_crawl_service.py
│   └── integration/
│       └── test_database.py
├── k8s/                      # Kubernetes 매니페스트
│   ├── base/
│   │   ├── kustomization.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── configmap.yaml
│   └── overlays/dev/
│       └── kustomization.yaml
├── argocd/                   # ArgoCD 설정
│   └── application.yaml
└── docs/                     # 문서
    ├── error_log.md          # 에러 이벤트 기록
    ├── change_log.md         # 변경 로그
    └── test_results/         # 테스트 결과 파일
```

---

## 3. 데이터베이스 구조

PostgreSQL을 사용하며, 애플리케이션 시작 시 테이블이 자동 생성됩니다.

### 테이블 구조

#### users
사용자 정보를 저장합니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `user_id` | BIGINT | Discord 사용자 ID (PK) |
| `created_at` | TIMESTAMP | 등록 시간 |

#### keywords
사용자별 알림 키워드를 저장합니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL | 키워드 ID (PK) |
| `user_id` | BIGINT | Discord 사용자 ID (FK → users) |
| `keyword` | TEXT | 키워드 내용 |
| `created_at` | TIMESTAMP | 등록 시간 |

- UNIQUE(user_id, keyword): 사용자별 키워드 중복 방지
- ON DELETE CASCADE: 사용자 삭제 시 키워드 자동 삭제

#### user_categories
사용자별 구독 카테고리를 저장합니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL | ID (PK) |
| `user_id` | BIGINT | Discord 사용자 ID (FK → users) |
| `category` | TEXT | 카테고리명 |
| `created_at` | TIMESTAMP | 등록 시간 |

- UNIQUE(user_id, category): 사용자별 카테고리 중복 방지
- ON DELETE CASCADE: 사용자 삭제 시 카테고리 자동 삭제

#### hotdeals
크롤링된 핫딜 정보를 저장합니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL | 핫딜 ID (PK) |
| `title` | TEXT | 핫딜 제목 |
| `price` | TEXT | 가격 정보 |
| `url` | TEXT | 핫딜 URL (UNIQUE) |
| `source` | TEXT | 출처 (예: Arca Live) |
| `created_at` | TIMESTAMP | 저장 시간 |

- 24시간 이상 된 데이터는 자동 삭제

#### crawl_state
크롤러의 마지막 크롤링 상태를 저장합니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `crawler_name` | TEXT | 크롤러 이름 (PK) |
| `last_post_id` | TEXT | 마지막으로 처리한 게시글 ID |
| `last_post_url` | TEXT | 마지막으로 처리한 게시글 URL |
| `last_post_datetime` | TIMESTAMP | 마지막 게시글 작성 시간 |
| `updated_at` | TIMESTAMP | 상태 업데이트 시간 |

#### notification_channels
서버별 알림 채널을 저장합니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `guild_id` | BIGINT | Discord 서버 ID (PK) |
| `channel_id` | BIGINT | 알림 채널 ID |
| `updated_at` | TIMESTAMP | 업데이트 시간 |

#### pending_analysis *(AI 분석 선택 기능)*
AI 분석 대기 항목을 저장합니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL | ID (PK) |
| `post_url` | TEXT | 분석 대상 게시글 URL (UNIQUE) |
| `post_title` | TEXT | 게시글 제목 |
| `scheduled_at` | TIMESTAMP | 분석 실행 예정 시각 (1차 알림 + 3시간) |
| `status` | TEXT | 처리 상태 (pending / processing / done / failed) |
| `retry_count` | INTEGER | 재시도 횟수 (최대 3회, 초과 시 failed 확정) |
| `created_at` | TIMESTAMP | 생성 시간 |

#### notification_history *(AI 분석 선택 기능)*
1차 알림 수신자를 기록합니다. AI 2차 알림 전송 대상 조회에 사용됩니다.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL | ID (PK) |
| `post_url` | TEXT | 게시글 URL (FK → pending_analysis) |
| `user_id` | BIGINT | 알림 수신 사용자 ID |
| `created_at` | TIMESTAMP | 기록 시간 |

- UNIQUE(post_url, user_id): 동일 게시글에 동일 사용자 중복 기록 방지

### 테이블 관계

```
users (1) ──── (N) keywords
users (1) ──── (N) user_categories
pending_analysis (1) ──── (N) notification_history
```

---

## 4. 사용 기술 및 선택 이유

| 기술 | 버전 | 선택 이유 |
|------|------|-----------|
| **Python** | 3.12 | discord.py 생태계와 비동기 지원 |
| **discord.py** | ≥2.3.0 | Discord 봇 개발 표준 라이브러리, slash command 지원 |
| **asyncpg** | ≥0.29.0 | PostgreSQL 비동기 드라이버 중 가장 빠른 성능 |
| **aiohttp** | ≥3.9.0 | 비동기 HTTP 요청, discord.py와 동일한 이벤트 루프 사용 |
| **BeautifulSoup4** | ≥4.12.0 | HTML 파싱이 직관적이고 셀렉터 지원이 풍부 |
| **python-dateutil** | ≥2.8.0 | ISO 8601 datetime 파싱 유연성 |
| **google-genai** | ≥1.0.0 | Google Gemini AI API 클라이언트 *(AI 분석 선택 기능, 무료 티어 1500 req/day)* |
| **PostgreSQL** | - | 안정적인 관계형 DB, UPSERT(ON CONFLICT) 지원으로 중복 처리 간편 |
| **Docker / Docker Compose** | - | 환경 일관성 보장, 홈 서버 배포 용이 |
| **Kubernetes + ArgoCD** | - | GitOps 기반 자동 배포, 선언적 배포 관리 |

---

## 5. 설치 및 실행 방법

### 환경 변수

`.env.example`을 복사해 `.env` 파일을 생성하세요.

| 변수명 | 필수 | 기본값 | 설명 |
|--------|------|--------|------|
| `DISCORD_TOKEN` | ✅ | - | Discord 봇 토큰 |
| `DATABASE_URL` | ✅ | `postgresql://root:root@localhost:5432/studydb` | PostgreSQL 연결 URL |
| `COMMAND_PREFIX` | ❌ | `!` | 봇 명령어 접두사 |
| `CRAWL_INTERVAL` | ❌ | `3600` | 크롤링 간격 (초) |
| `LOG_LEVEL` | ❌ | `INFO` | 로그 레벨 |
| `LOG_FILE` | ❌ | `hotdeal_bot.log` | 로그 파일명 |
| `GEMINI_API_KEY` | ❌ | - | Google Gemini API Key (미설정 시 AI 분석 비활성화, 발급: aistudio.google.com) |
| `AI_ANALYSIS_DELAY_HOURS` | ❌ | `3` | AI 분석 실행 지연 시간 (시간 단위) |

### 로컬 실행 (venv)

```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일에 DISCORD_TOKEN, DATABASE_URL 설정

# 4. 봇 실행
python bot.py
```

### 테스트 실행

```bash
source venv/bin/activate

# 전체 테스트 (73개)
python -m pytest tests/ -v

# 유닛 테스트만 (DB 불필요)
python -m pytest tests/unit/ -v

# 통합 테스트만 (hotdeal_test DB 필요)
python -m pytest tests/integration/ -v
```

### Docker Compose (로컬 개발용)

```bash
docker-compose up -d --build
docker-compose logs -f
docker-compose down
```

### Kubernetes 배포 (ArgoCD)

```bash
# 1. Secret 생성
kubectl create secret generic hotdeal-bot-secret \
  -n hotdeal-bot-dev \
  --from-literal=DISCORD_TOKEN='YOUR_TOKEN'

# 2. AI 분석 기능 사용 시 API Key 추가 (선택)
kubectl patch secret dev-hotdeal-bot-secret \
  -n hotdeal-bot-dev \
  --type='json' \
  -p='[{"op":"add","path":"/data/GEMINI_API_KEY","value":"'$(echo -n "AIza..." | base64)'"}]'

# 3. ArgoCD Application 등록
kubectl apply -f argocd/application.yaml

# 4. 이미지 태그 변경 후 push → ArgoCD 자동 배포
# k8s/overlays/dev/kustomization.yaml 의 newTag 값 수정 후 git push
```

### Discord 봇 설정

1. [Discord Developer Portal](https://discord.com/developers/applications/)에서 봇 생성
2. Bot 탭에서 **MESSAGE CONTENT INTENT** 활성화 (필수)
3. OAuth2 → URL Generator에서 `bot` + `applications.commands` 스코프 선택 후 초대 URL 생성
4. 발급받은 토큰을 `.env`의 `DISCORD_TOKEN`에 설정

---

## 6. 에러 모음

에러 이벤트 및 해결 방법은 [docs/error_log.md](docs/error_log.md)를 참고하세요.

| 에러 | 원인 | 해결 방법 |
|------|------|-----------|
| `LoginFailure` | 봇 토큰이 유효하지 않음 | `DISCORD_TOKEN` 환경 변수 확인 |
| `asyncpg.exceptions.ConnectionFailureError` | DB 연결 실패 | `DATABASE_URL` 및 PostgreSQL 서버 상태 확인 |
| `ImagePullBackOff` (k8s) | 로컬 이미지를 찾지 못함 | `docker build` 후 `imagePullPolicy: Never` 확인 |
| `ExtensionAlreadyLoaded` | `on_ready` 재호출로 명령어 중복 로드 | 봇 재시작 또는 코드 중복 로드 방어 처리 확인 |
| 명령어 응답이 두 번 옴 | 동일 토큰으로 봇 인스턴스 2개 실행 중 | `docker ps \| grep hotdeal`로 확인 후 중복 컨테이너 중지 |
| AI 분석이 동작하지 않음 | `GEMINI_API_KEY` 미설정 | `.env` 또는 k8s Secret에 API Key 추가 후 재시작 |
| 2차 알림이 오지 않음 | `pending_analysis` status 고착 | DB에서 `status='processing'` 항목을 `'pending'`으로 초기화 |
| `AttributeError: Settings has no attribute 'ANTHROPIC_API_KEY'` | SDK 교체 후 설정 참조 누락 | `grep -rn ANTHROPIC_API_KEY` 로 잔존 참조 확인 후 `GEMINI_API_KEY`로 교체 |
| `404 NOT_FOUND: models/gemini-1.5-flash` | 모델 지원 종료 | `gemini-2.5-flash` 로 변경 |
| `429 RESOURCE_EXHAUSTED limit: 0` | 계정에서 해당 모델 free tier 미할당 | 사용 가능한 모델 확인 후 변경 (`gemini-2.5-flash` 권장) |

---

## 라이선스

MIT
