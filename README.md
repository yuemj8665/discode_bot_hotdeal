# 핫딜 봇 (Hotdeal Bot)

Discord에서 Arca Live 핫딜 정보를 자동으로 모니터링하고 키워드 매칭 알림을 제공하는 봇입니다.

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
- **키워드 관리**: 사용자별 키워드 추가 / 삭제 / 목록 조회 (CRUD)
- **중복 방지**: 마지막 게시글 ID / URL / 작성 시간 기반 중복 알림 방지
- **데이터 정리**: 24시간 이상 된 핫딜 데이터 자동 삭제

### 봇 명령어

| 명령어 | 설명 |
|--------|------|
| `!ping` | 봇 응답 속도 확인 |
| `!정보` | 봇 정보 확인 |
| `!키워드 추가 [단어]` | 감시할 키워드 추가 |
| `!키워드 삭제 [단어]` | 등록된 키워드 삭제 |
| `!키워드 목록` | 등록된 키워드 목록 확인 |
| `/핫딜` | 최근 핫딜 목록 조회 (슬래시 명령어) |

### 알림 동작 방식

1. 키워드 등록 사용자에게 키워드 매칭 핫딜 발견 시 자동 알림
2. DM 전송 우선 → DM 불가 시 서버 지정 채널 or `general` 채널로 폴백
3. `*` 키워드 등록 시 모든 핫딜에 매칭 (와일드카드)

---

## 2. 프로젝트 구조

```
discode_bot_hotdeal/
├── bot.py                    # 봇 메인 진입점
├── requirements.txt          # Python 의존성
├── Dockerfile                # Docker 이미지 빌드 파일
├── docker-compose.yml        # 로컬 개발용 Docker Compose
├── docker-compose.yaml       # 홈 서버 배포용 Docker Compose
├── deploy.sh                 # 자동 배포 스크립트 (k8s)
├── .env.example              # 환경 변수 예시 파일
├── config/                   # 설정 모듈
│   ├── __init__.py
│   ├── settings.py           # 환경 변수 관리
│   └── logging_config.py     # 로깅 설정
├── commands/                 # 봇 명령어 모듈
│   ├── __init__.py
│   ├── hotdeal.py            # 핫딜 조회 명령어
│   └── keyword.py            # 키워드 관리 명령어
├── crawling/                 # 크롤링 모듈
│   ├── __init__.py
│   ├── base.py               # 기본 크롤러 클래스
│   └── crawler.py            # Arca Live 핫딜 크롤러 구현
├── database/                 # 데이터베이스 모듈
│   ├── __init__.py
│   ├── models.py             # 데이터 모델 (Hotdeal, User, Keyword)
│   └── db.py                 # 비동기 PostgreSQL 연결 및 쿼리
├── services/                 # 서비스 레이어
│   ├── __init__.py
│   ├── crawl_service.py      # 크롤링 파이프라인 (fetch → filter → save → notify)
│   └── notification_service.py # Discord 알림 전송
├── utils/                    # 유틸리티 모듈
│   ├── __init__.py
│   └── helpers.py            # 공통 유틸리티 함수
├── k8s/                      # Kubernetes 매니페스트
│   ├── base/
│   │   ├── kustomization.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── configmap.yaml
│   └── overlays/dev/
│       └── kustomization.yaml
├── argocd/                   # ArgoCD 설정
│   ├── application.yaml
│   └── README.md
└── docs/                     # 문서
    ├── error_log.md          # 에러 이벤트 기록
    └── change_log.md         # 변경 로그
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
- 인덱스: `idx_keywords_user_id`, `idx_keywords_keyword`

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

- 인덱스: `idx_url`
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

### 테이블 관계

```
users (1) ──── (N) keywords
```

---

## 4. 사용 기술 및 선택 이유

| 기술 | 버전 | 선택 이유 |
|------|------|-----------|
| **Python** | 3.x | discord.py 생태계와 비동기 지원 |
| **discord.py** | ≥2.3.0 | Discord 봇 개발 표준 라이브러리, slash command 지원 |
| **asyncpg** | ≥0.29.0 | PostgreSQL 비동기 드라이버 중 가장 빠른 성능 |
| **aiohttp** | ≥3.9.0 | 비동기 HTTP 요청, discord.py와 동일한 이벤트 루프 사용 |
| **BeautifulSoup4** | ≥4.12.0 | HTML 파싱이 직관적이고 셀렉터 지원이 풍부 |
| **python-dateutil** | ≥2.8.0 | ISO 8601 datetime 파싱 유연성 |
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

### Docker Compose (로컬 개발용)

```bash
# 이미지 빌드 및 실행 (PostgreSQL 포함)
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 종료
docker-compose down
```

### 홈 서버 배포 (Docker Compose)

```bash
# 로그 디렉토리 생성
mkdir -p /Users/mamyeongjae/home-server/data/services/personal/hotdeal-bot/logs

# docker-compose.yaml 심볼릭 링크 생성
mkdir -p /Users/mamyeongjae/home-server/services/personal/hotdeal-bot
ln -s $(pwd)/docker-compose.yaml \
      /Users/mamyeongjae/home-server/services/personal/hotdeal-bot/docker-compose.yaml

# 실행
cd /Users/mamyeongjae/home-server/services/personal/hotdeal-bot
docker-compose up -d --build
```

### Kubernetes 배포 (ArgoCD)

```bash
# 1. Secret 생성
kubectl create secret generic hotdeal-bot-secret \
  -n hotdeal-bot-dev \
  --from-literal=DISCORD_TOKEN='YOUR_TOKEN'

# 2. ArgoCD Application 등록
kubectl apply -f argocd/application.yaml

# 3. 자동 배포 스크립트 실행
./deploy.sh "배포 메시지"
```

자세한 내용은 [argocd/README.md](argocd/README.md) 참고.

### Discord 봇 설정

1. [Discord Developer Portal](https://discord.com/developers/applications/)에서 봇 생성
2. Bot 탭에서 **MESSAGE CONTENT INTENT** 활성화 (필수)
3. OAuth2 → URL Generator에서 `bot` + `applications.commands` 스코프, 필요한 권한 선택 후 초대 URL 생성
4. 발급받은 토큰을 `.env`의 `DISCORD_TOKEN`에 설정

---

## 6. 에러 모음

에러 이벤트 및 해결 방법은 [docs/error_log.md](docs/error_log.md)를 참고하세요.

| 에러 | 원인 | 해결 방법 |
|------|------|-----------|
| `LoginFailure` | 봇 토큰이 유효하지 않음 | `DISCORD_TOKEN` 환경 변수 확인 |
| `asyncpg.exceptions.ConnectionFailureError` | DB 연결 실패 | `DATABASE_URL` 및 PostgreSQL 서버 상태 확인 |
| `ImagePullBackOff` (k8s) | 로컬 이미지를 찾지 못함 | `docker build` 후 `imagePullPolicy: Never` 확인 |
| `ExtensionAlreadyLoaded` | `on_ready` 재호출로 명령어 중복 로드 | 봇 재시작 또는 코드 중복 로드 방어 처리 |
| 대량 알림 발생 | 마지막 URL 미확인으로 전체 게시글 알림 | `crawl_state` 테이블 최신 상태 확인 |

---

## 라이선스

MIT
