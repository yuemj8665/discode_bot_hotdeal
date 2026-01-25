# 핫딜 봇 (Hotdeal Bot)

Discord에서 핫딜 정보를 모니터링하고 알림을 제공하는 봇입니다.

## 기능

- 핫딜 정보 크롤링 및 저장
- 핫딜 목록 조회 명령어
- 주기적인 크롤링 자동 실행
- 데이터베이스에 핫딜 정보 저장
- 사용자별 키워드 저장 및 관리 (CRUD)

## 프로젝트 구조

```
discode_bot_hotdeal/
├── bot.py                 # 봇 메인 진입점
├── config/                # 설정 모듈
│   ├── __init__.py
│   ├── settings.py        # 환경 변수 관리
│   └── logging_config.py  # 로깅 설정
├── commands/              # 봇 명령어 모듈
│   ├── __init__.py
│   └── hotdeal.py         # 핫딜 관련 명령어
├── crawling/              # 크롤링 모듈
│   ├── __init__.py
│   ├── base.py            # 기본 크롤러 클래스
│   └── crawler.py         # 핫딜 크롤러 구현
├── database/              # 데이터베이스 모듈
│   ├── __init__.py
│   ├── models.py          # 데이터 모델
│   └── db.py              # 데이터베이스 연결 및 작업
├── utils/                 # 유틸리티 모듈
│   ├── __init__.py
│   └── helpers.py         # 유틸리티 함수
├── k8s/                   # Kubernetes 매니페스트
│   ├── base/              # 기본 리소스
│   │   ├── kustomization.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── configmap.yaml
│   └── overlays/          # 환경별 오버레이
│       └── dev/           # 개발 환경
│           └── kustomization.yaml
├── argocd/                # ArgoCD 설정
│   ├── application.yaml   # ArgoCD Application 정의
│   └── README.md          # ArgoCD 배포 가이드
├── requirements.txt       # Python 의존성
├── Dockerfile             # Docker 이미지 빌드 파일
├── docker-compose.yml     # Docker Compose 설정
├── deploy.sh              # 자동 배포 스크립트
├── .env.example           # 환경 변수 예시 파일
└── README.md              # 이 파일
```

## 설치 및 실행

### 로컬에서 실행하기

#### 1. 가상환경 설정

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows
```

#### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

#### 3. PostgreSQL 데이터베이스 설정

PostgreSQL 데이터베이스를 설치하고 데이터베이스를 생성하세요:

```bash
# PostgreSQL 설치 (macOS)
brew install postgresql
brew services start postgresql

# 데이터베이스 생성
createdb studydb
```

#### 4. 환경 변수 설정

`.env` 파일을 생성하고 Discord 봇 토큰 및 데이터베이스 URL을 설정하세요:

```bash
cp .env.example .env
# .env 파일을 편집하여 DISCORD_TOKEN과 DATABASE_URL을 설정하세요
```

또는 환경 변수로 직접 설정:

```bash
export DISCORD_TOKEN=your_discord_bot_token_here
export DATABASE_URL=postgresql://root:root@localhost:5432/studydb
```

#### 5. 봇 실행

```bash
python bot.py
```

## 홈 서버 배포 (Docker Compose)

### 사전 준비

1. **디렉토리 생성**
```bash
# 로그 저장 디렉토리 생성
mkdir -p /Users/mamyeongjae/home-server/data/services/personal/hotdeal-bot/logs
```

2. **환경 변수 설정**

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 입력하세요:

```bash
# Discord 봇 토큰 (필수)
DISCORD_TOKEN=your_discord_bot_token_here

# PostgreSQL 설정 (기존 PostgreSQL 서버 사용)
# 로컬 PostgreSQL 사용 시: postgresql://root:root@localhost:5432/studydb
# 원격 PostgreSQL 사용 시: postgresql://user:password@host:port/database
DATABASE_URL=postgresql://root:root@localhost:5432/studydb

# 크롤링 간격 (초 단위, 기본값: 60초 = 1분)
CRAWL_INTERVAL=60

# 로그 설정
LOG_LEVEL=INFO
LOG_FILE=hotdeal_bot.log
```

**참고**: 기존 PostgreSQL 서버를 사용하므로 별도의 PostgreSQL 컨테이너는 실행하지 않습니다.

### 배포 및 실행

1. **docker-compose.yaml 파일 위치**

홈 서버 배포용 `docker-compose.yaml` 파일은 프로젝트 루트에 있습니다.
이 파일은 다음을 포함합니다:
- 타임존 설정 (Asia/Seoul)
- 로그 파일 영구 저장 볼륨 마운트
- 호스트 네트워크 모드 (기존 PostgreSQL 서버 연결용)
- **참고**: PostgreSQL 서비스는 포함되지 않음 (기존 PostgreSQL 서버 사용)

2. **docker-compose.yaml 파일 배치**

홈 서버 배포용 `docker-compose.yaml` 파일을 `/Users/mamyeongjae/home-server/services/personal/hotdeal-bot/` 디렉토리에 복사하거나 심볼릭 링크를 생성하세요:

```bash
# 디렉토리 생성
mkdir -p /Users/mamyeongjae/home-server/services/personal/hotdeal-bot

# docker-compose.yaml 복사 또는 심볼릭 링크 생성
cp /Users/mamyeongjae/home-server/workspace/personal/discode_bot_hotdeal/docker-compose.yaml \
   /Users/mamyeongjae/home-server/services/personal/hotdeal-bot/docker-compose.yaml

# 또는 심볼릭 링크 (권장)
ln -s /Users/mamyeongjae/home-server/workspace/personal/discode_bot_hotdeal/docker-compose.yaml \
      /Users/mamyeongjae/home-server/services/personal/hotdeal-bot/docker-compose.yaml
```

3. **컨테이너 실행**

```bash
# 서비스 디렉토리로 이동
cd /Users/mamyeongjae/home-server/services/personal/hotdeal-bot

# 이미지 빌드 및 컨테이너 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그만 확인
docker-compose logs -f discord-bot
docker-compose logs -f postgres
```

4. **컨테이너 관리**

```bash
# 서비스 디렉토리로 이동
cd /Users/mamyeongjae/home-server/services/personal/hotdeal-bot

# 컨테이너 중지
docker-compose down

# 컨테이너 재시작
docker-compose restart

# 컨테이너 상태 확인
docker-compose ps

# 컨테이너 중지 및 볼륨 삭제 (주의: 데이터 삭제됨)
docker-compose down -v
```

### 데이터 영구 저장

다음 디렉토리에 데이터가 영구 저장됩니다:

- **로그 파일**: `/Users/mamyeongjae/home-server/data/services/personal/hotdeal-bot/logs`

**참고**: PostgreSQL 데이터는 기존 PostgreSQL 서버에 저장되므로 별도 볼륨 마운트가 필요하지 않습니다.

### 타임존 설정

모든 컨테이너는 `Asia/Seoul` 타임존으로 설정되어 있습니다:
- 봇 컨테이너: `TZ=Asia/Seoul` 환경 변수
- PostgreSQL 컨테이너: `TZ=Asia/Seoul`, `PGTZ=Asia/Seoul` 환경 변수

## Kubernetes 배포 (ArgoCD)

이 프로젝트는 ArgoCD를 사용하여 Kubernetes에 배포됩니다.

### 사전 준비

#### 1. OrbStack Kubernetes 시작

```bash
# Kubernetes 클러스터 시작
orbctl start k8s

# 클러스터 상태 확인
kubectl cluster-info
```

#### 2. ArgoCD 상태 확인

```bash
# ArgoCD Pod 상태 확인
kubectl get pods -n argocd

# ArgoCD 서비스 확인
kubectl get svc -n argocd
```

#### 3. Secret 생성

Discord 봇 토큰을 Kubernetes Secret으로 설정:

```bash
# Secret 생성 (실제 토큰으로 변경)
kubectl create secret generic hotdeal-bot-secret \
  -n hotdeal-bot-dev \
  --from-literal=DISCORD_TOKEN='YOUR_ACTUAL_DISCORD_TOKEN'

# Secret 확인
kubectl get secret hotdeal-bot-secret -n hotdeal-bot-dev

# Secret 내용 확인 (base64 디코딩)
kubectl get secret hotdeal-bot-secret -n hotdeal-bot-dev -o jsonpath="{.data.DISCORD_TOKEN}" | base64 -d
```

#### 4. PostgreSQL 서비스 설정

데이터베이스 연결을 위해 PostgreSQL 서비스가 필요합니다. ConfigMap의 `DATABASE_URL`을 확인하세요:

```bash
# ConfigMap 확인
kubectl get configmap dev-hotdeal-bot-config -n hotdeal-bot-dev -o yaml

# ConfigMap 수정 (필요시)
kubectl edit configmap dev-hotdeal-bot-config -n hotdeal-bot-dev
```

### ArgoCD Application 등록

```bash
# 프로젝트 디렉토리로 이동
cd /Users/mamyeongjae/home-server/workspace/personal/discode_bot_hotdeal

# ArgoCD Application 등록
kubectl apply -f argocd/application.yaml

# 등록 확인
kubectl get applications -n argocd

# Application 상태 확인
kubectl get application hotdeal-bot-dev -n argocd -o yaml
```

### 이미지 빌드 및 배포

#### 자동 배포 스크립트 사용 (권장)

```bash
# 배포 스크립트 실행
./deploy.sh "커밋 메시지"

# 또는 커밋 메시지 없이 실행
./deploy.sh
```

배포 스크립트는 다음 작업을 수행합니다:
1. Docker 이미지 빌드 (태그: `hotdeal-bot:YYYYMMDD_HHMM` 형식)
2. `kustomization.yaml`의 이미지 태그 자동 업데이트
3. Git 커밋 및 푸시
4. ArgoCD가 자동으로 배포 감지 및 적용

#### 수동 배포

```bash
# 1. 이미지 태그 생성 (날짜_시간분 형식)
TAG=$(date +%Y%m%d_%H%M)
echo "태그: $TAG"

# 2. Docker 이미지 빌드
docker build -t hotdeal-bot:${TAG} .

# 3. kustomization.yaml 업데이트
sed -i '' "s/newTag: .*/newTag: \"${TAG}\"/" k8s/overlays/dev/kustomization.yaml

# 4. Git 커밋 및 푸시
git add .
git commit -m "Deploy version ${TAG}"
git push

# ArgoCD가 자동으로 변경사항을 감지하여 배포합니다
```

### 배포 상태 확인

```bash
# Pod 상태 확인
kubectl get pods -n hotdeal-bot-dev

# Pod 상세 정보 확인
kubectl describe pod -n hotdeal-bot-dev -l app=hotdeal-bot

# Pod 로그 확인
kubectl logs -f deployment/dev-hotdeal-bot -n hotdeal-bot-dev

# 또는 특정 Pod 로그 확인
kubectl logs -f <pod-name> -n hotdeal-bot-dev

# Deployment 상태 확인
kubectl get deployment -n hotdeal-bot-dev

# Service 상태 확인
kubectl get svc -n hotdeal-bot-dev
```

### 배포 재시작

```bash
# Deployment 재시작
kubectl rollout restart deployment/dev-hotdeal-bot -n hotdeal-bot-dev

# 재시작 후 상태 확인
kubectl rollout status deployment/dev-hotdeal-bot -n hotdeal-bot-dev
```

### ArgoCD 접속

#### 로컬 포트 포워딩

```bash
# ArgoCD 서버 포트 포워딩 (HTTPS)
kubectl port-forward svc/argocd-server -n argocd 8081:443 &

# 포트 포워딩 상태 확인
lsof -i :8081

# 접속 정보
# URL: https://localhost:8081
# Username: admin
# Password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

#### ngrok을 사용한 외부 접속

```bash
# 1. ArgoCD 포트 포워딩 시작
kubectl port-forward svc/argocd-server -n argocd 8081:443 > /dev/null 2>&1 &

# 2. ngrok 실행
ngrok http 8081

# ngrok이 생성한 URL로 ArgoCD에 접속 가능
# 예: https://xxxx-xx-xx-xxx-xxx.ngrok-free.app
```

**주의**: ngrok 명령어는 포트 번호만 사용합니다:
- ❌ `ngrok http https://localhost:8081` (잘못된 형식)
- ✅ `ngrok http 8081` (올바른 형식)

### 문제 해결

#### Pod가 시작되지 않음

```bash
# Pod 이벤트 확인
kubectl describe pod <pod-name> -n hotdeal-bot-dev

# Pod 로그 확인
kubectl logs <pod-name> -n hotdeal-bot-dev

# 이전 컨테이너 로그 확인 (재시작된 경우)
kubectl logs <pod-name> -n hotdeal-bot-dev --previous
```

#### ImagePullBackOff 오류

```bash
# 이미지 태그 확인
kubectl describe pod <pod-name> -n hotdeal-bot-dev | grep Image:

# 로컬 이미지 확인
docker images | grep hotdeal-bot

# 이미지 재빌드 및 태그 업데이트
TAG=$(date +%Y%m%d_%H%M)
docker build -t hotdeal-bot:${TAG} .
sed -i '' "s/newTag: .*/newTag: \"${TAG}\"/" k8s/overlays/dev/kustomization.yaml
kubectl apply -k k8s/overlays/dev
```

#### Secret 오류

```bash
# Secret 확인
kubectl get secret hotdeal-bot-secret -n hotdeal-bot-dev

# Secret 재생성
kubectl delete secret hotdeal-bot-secret -n hotdeal-bot-dev
kubectl create secret generic hotdeal-bot-secret \
  -n hotdeal-bot-dev \
  --from-literal=DISCORD_TOKEN='YOUR_TOKEN'
```

#### 데이터베이스 연결 실패

```bash
# ConfigMap 확인
kubectl get configmap dev-hotdeal-bot-config -n hotdeal-bot-dev -o yaml

# DATABASE_URL 수정
kubectl edit configmap dev-hotdeal-bot-config -n hotdeal-bot-dev

# Pod 재시작
kubectl rollout restart deployment/dev-hotdeal-bot -n hotdeal-bot-dev
```

#### 네임스페이스 확인

```bash
# 네임스페이스 목록 확인
kubectl get namespaces

# 네임스페이스 생성 (필요시)
kubectl create namespace hotdeal-bot-dev

# 네임스페이스의 모든 리소스 확인
kubectl get all -n hotdeal-bot-dev
```

### 이미지 태그 형식

이미지 태그는 날짜_시간분 형식을 사용합니다:
- 형식: `hotdeal-bot:YYYYMMDD_HHMM`
- 예시: `hotdeal-bot:20260126_0020`

`deploy.sh` 스크립트가 자동으로 현재 시간을 태그로 생성합니다.

### 주의사항

1. **헬스체크 없음**: Discord 봇은 HTTP 서버가 아니므로 liveness/readiness probe를 사용하지 않습니다.
2. **Secret 관리**: Discord 토큰은 반드시 Secret으로 관리하고 Git에 커밋하지 마세요.
3. **데이터베이스 연결**: PostgreSQL 서비스가 네임스페이스 내에 있어야 합니다.
4. **이미지 빌드**: 로컬에서 빌드한 이미지는 `imagePullPolicy: Never`로 설정되어 있어 OrbStack에서 사용 가능합니다.
5. **namePrefix**: `kustomization.yaml`의 `namePrefix: dev-`로 인해 리소스 이름이 `dev-`로 시작합니다.

## Docker로 실행하기 (로컬 개발용)

### 1. 환경 변수 설정

`.env` 파일을 생성하고 Discord 봇 토큰 및 PostgreSQL 설정을 입력하세요:

```bash
DISCORD_TOKEN=your_discord_bot_token_here
DATABASE_URL=postgresql://hotdeal:hotdeal_password@postgres:5432/hotdeal
POSTGRES_USER=hotdeal
POSTGRES_PASSWORD=hotdeal_password
POSTGRES_DB=hotdeal
```

### 2. Docker Compose로 실행

Docker Compose를 사용하면 PostgreSQL 서버가 자동으로 시작됩니다:

```bash
# 이미지 빌드 및 컨테이너 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 컨테이너 중지
docker-compose down
```

### 3. Docker 명령어로 직접 실행

```bash
# 이미지 빌드
docker build -t hotdeal-bot .

# 컨테이너 실행
docker run -d \
  --name hotdeal-bot \
  --restart unless-stopped \
  --env-file .env \
  hotdeal-bot

# 로그 확인
docker logs -f hotdeal-bot

# 컨테이너 중지
docker stop hotdeal-bot
docker rm hotdeal-bot
```

## 환경 변수

| 변수명 | 설명 | 필수 | 기본값 |
|--------|------|------|--------|
| `DISCORD_TOKEN` | Discord 봇 토큰 | ✅ | - |
| `COMMAND_PREFIX` | 명령어 접두사 | ❌ | `!` |
| `DATABASE_URL` | PostgreSQL 데이터베이스 URL | ✅ | `postgresql://root:root@localhost:5432/studydb` |
| `POSTGRES_USER` | PostgreSQL 사용자명 (Docker Compose용) | ❌ | `hotdeal` |
| `POSTGRES_PASSWORD` | PostgreSQL 비밀번호 (Docker Compose용) | ❌ | `hotdeal_password` |
| `POSTGRES_DB` | PostgreSQL 데이터베이스명 (Docker Compose용) | ❌ | `hotdeal` |
| `POSTGRES_PORT` | PostgreSQL 포트 (Docker Compose용) | ❌ | `5432` |
| `CRAWL_INTERVAL` | 크롤링 간격 (초) | ❌ | `3600` |
| `LOG_LEVEL` | 로그 레벨 | ❌ | `INFO` |
| `LOG_FILE` | 로그 파일명 | ❌ | `hotdeal_bot.log` |

## 명령어

### 일반 명령어

- `!ping` - 봇의 응답 속도 확인
- `!정보` - 봇 정보 확인
- `!핫딜` - 핫딜 목록 조회 (구현 예정)

### 키워드 관리 명령어

- `!키워드 추가 [단어]` - 감시할 키워드 추가
  - 예: `!키워드 추가 노트북`
- `!키워드 삭제 [단어]` - 키워드 삭제
  - 예: `!키워드 삭제 노트북`
- `!키워드 목록` - 현재 등록된 키워드 목록 확인

### 슬래시 명령어

- `/핫딜` - 핫딜 목록 조회
- `/핫딜추가` - 핫딜 추가 (구현 예정)

### 알림 기능

- 키워드가 등록된 사용자는 키워드가 매칭된 새로운 핫딜 게시글이 발견되면 자동으로 알림을 받습니다.
- 알림은 우선 DM으로 전송되며, DM이 불가능한 경우 봇이 있는 채널에 맨션과 함께 전송됩니다.
- 크롤링은 1분마다 자동으로 실행됩니다.

## 데이터베이스 구조

### 테이블 구조

#### users 테이블
사용자 정보를 저장하는 테이블입니다.

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `user_id` | BIGINT | Discord 사용자 ID (PRIMARY KEY) |
| `created_at` | TIMESTAMP | 생성 시간 (기본값: CURRENT_TIMESTAMP) |

#### keywords 테이블
사용자별 키워드를 저장하는 테이블입니다.

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `id` | SERIAL | 키워드 ID (PRIMARY KEY) |
| `user_id` | BIGINT | Discord 사용자 ID (FOREIGN KEY → users.user_id) |
| `keyword` | TEXT | 키워드 내용 |
| `created_at` | TIMESTAMP | 생성 시간 (기본값: CURRENT_TIMESTAMP) |
| UNIQUE(user_id, keyword) | - | 사용자별 키워드 중복 방지 |

#### crawl_state 테이블
크롤러별 마지막 게시글 ID를 저장하는 테이블입니다.

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `crawler_name` | TEXT | 크롤러 이름 (PRIMARY KEY) |
| `last_post_id` | TEXT | 마지막으로 크롤링한 게시글 ID |
| `updated_at` | TIMESTAMP | 업데이트 시간 (기본값: CURRENT_TIMESTAMP) |

#### notification_channels 테이블
서버별 알림 채널을 저장하는 테이블입니다.

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `guild_id` | BIGINT | 서버 ID (PRIMARY KEY) |
| `channel_id` | BIGINT | 알림을 보낼 채널 ID |
| `updated_at` | TIMESTAMP | 업데이트 시간 (기본값: CURRENT_TIMESTAMP) |

#### hotdeals 테이블
핫딜 정보를 저장하는 테이블입니다.

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `id` | SERIAL | 핫딜 ID (PRIMARY KEY) |
| `title` | TEXT | 핫딜 제목 |
| `price` | TEXT | 가격 정보 |
| `url` | TEXT | 핫딜 URL (UNIQUE) |
| `source` | TEXT | 출처 |
| `created_at` | TIMESTAMP | 생성 시간 (기본값: CURRENT_TIMESTAMP) |

### 관계

- `keywords.user_id` → `users.user_id` (FOREIGN KEY, ON DELETE CASCADE)
  - 사용자가 삭제되면 해당 사용자의 모든 키워드도 자동 삭제됩니다.

### 인덱스

- `idx_keywords_user_id`: `keywords.user_id`에 대한 인덱스
- `idx_keywords_keyword`: `keywords.keyword`에 대한 인덱스
- `idx_url`: `hotdeals.url`에 대한 인덱스

### 데이터베이스 사용법

#### Database 클래스 초기화 및 연결

```python
from database import Database

# 데이터베이스 인스턴스 생성
db = Database()

# 연결 (비동기)
await db.connect()

# 사용 후 종료
await db.close()
```

#### 사용자 관련 함수

```python
# 사용자 추가
await db.add_user(user_id=123456789)

# 사용자 조회
user = await db.get_user(user_id=123456789)

# 사용자 삭제 (키워드도 함께 삭제됨)
await db.delete_user(user_id=123456789)
```

#### 키워드 관련 함수 (CRUD)

```python
# 키워드 추가 (Create)
await db.add_keyword(user_id=123456789, keyword="노트북")

# 키워드 목록 조회 (Read)
keywords = await db.get_keywords(user_id=123456789)
for keyword in keywords:
    print(f"키워드: {keyword.keyword}, 생성일: {keyword.created_at}")

# 키워드 삭제 (Delete)
await db.delete_keyword(user_id=123456789, keyword="노트북")

# 사용자의 모든 키워드 삭제
deleted_count = await db.delete_all_keywords(user_id=123456789)

# 특정 키워드를 가진 사용자 목록 조회
user_ids = await db.get_users_by_keyword(keyword="노트북")
```

#### 핫딜 관련 함수

```python
from database.models import Hotdeal

# 핫딜 추가
hotdeal = Hotdeal(
    title="삼성 노트북",
    price="500,000원",
    url="https://example.com/hotdeal/1",
    source="쿠팡"
)
await db.add_hotdeal(hotdeal)

# 핫딜 목록 조회
hotdeals = await db.get_hotdeals(limit=10)

# URL로 핫딜 조회
hotdeal = await db.get_hotdeal_by_url("https://example.com/hotdeal/1")
```

### 비동기 지원

모든 데이터베이스 함수는 `async/await`를 사용하는 비동기 함수입니다. `asyncpg`를 사용하여 PostgreSQL과 비동기 통신을 수행합니다.

### PostgreSQL에서 직접 조회하기

PostgreSQL에 직접 접속하여 키워드를 조회할 수 있습니다:

```bash
# PostgreSQL 접속 (로컬)
psql -U root -d studydb

# 또는 Docker 컨테이너를 통해 접속
docker exec -it study-postgres psql -U root -d studydb
```

#### 유용한 SQL 쿼리

```sql
-- 모든 키워드 조회 (사용자별)
SELECT 
    k.user_id,
    k.keyword,
    k.created_at
FROM keywords k
ORDER BY k.user_id, k.created_at DESC;

-- 특정 사용자의 키워드 조회
SELECT keyword, created_at
FROM keywords
WHERE user_id = 663061539301097489
ORDER BY created_at DESC;

-- 키워드별 사용자 수 통계
SELECT 
    keyword,
    COUNT(*) as user_count,
    STRING_AGG(user_id::text, ', ') as user_ids
FROM keywords
GROUP BY keyword
ORDER BY user_count DESC;

-- 전체 키워드 개수
SELECT COUNT(*) as total_keywords FROM keywords;

-- 사용자별 키워드 개수
SELECT 
    user_id,
    COUNT(*) as keyword_count
FROM keywords
GROUP BY user_id
ORDER BY keyword_count DESC;

-- 특정 키워드를 가진 모든 사용자 조회
SELECT DISTINCT user_id
FROM keywords
WHERE keyword = '노트북';

-- 최근 추가된 키워드 (최근 10개)
SELECT user_id, keyword, created_at
FROM keywords
ORDER BY created_at DESC
LIMIT 10;
```

## 개발

### 모듈 구조

- **config**: 환경 변수 및 로깅 설정 관리
- **commands**: Discord 봇 명령어 구현
- **crawling**: 웹 크롤링 로직 구현
- **database**: PostgreSQL 데이터베이스 연결 및 데이터 관리 (비동기)
- **utils**: 공통 유틸리티 함수

### 크롤링 기능

#### Arca Live 핫딜 크롤러

현재 구현된 크롤러는 **Arca Live 핫딜 게시판** (https://arca.live/b/hotdeal)을 크롤링합니다.

**주요 기능:**
- 비동기 크롤링 (aiohttp + BeautifulSoup)
- 마지막 게시글 ID 저장으로 중복 알림 방지
- 키워드 매칭: 게시글 제목에 사용자 키워드가 포함되어 있는지 자동 검사
- 새로운 게시글만 필터링하여 알림

**크롤링 프로세스:**
1. Arca Live 핫딜 게시판에서 최신 게시글 목록 가져오기
2. 마지막으로 크롤링한 게시글 ID와 비교하여 새로운 게시글만 추출
3. 각 게시글 제목에 사용자 키워드가 포함되어 있는지 검사
4. 키워드가 매칭된 게시글을 데이터베이스에 저장
5. 매칭된 사용자에게 알림 (구현 예정)

**크롤링 간격:**
- 기본값: 3600초 (1시간)
- `.env` 파일의 `CRAWL_INTERVAL`로 설정 가능

### 새로운 크롤러 추가하기

1. `crawling/crawler.py`를 수정하거나 새로운 크롤러 클래스를 생성
2. `BaseCrawler`를 상속받아 `fetch()`와 `parse()` 메서드 구현
3. `crawl()` 메서드를 오버라이드하여 새로운 글 필터링 로직 추가
4. `bot.py`에서 크롤러 인스턴스 생성 및 사용

### 새로운 명령어 추가하기

1. `commands/` 디렉토리에 새로운 파일 생성 또는 기존 파일 수정
2. `commands.Cog`를 상속받는 클래스 생성
3. `bot.py`에서 `load_extension()`으로 로드

## Discord 봇 설정 가이드

### 1. Discord Developer Portal에서 봇 생성

1. **Discord Developer Portal 접속**
   - https://discord.com/developers/applications/ 접속
   - Discord 계정으로 로그인

2. **새 애플리케이션 생성**
   - 우측 상단의 "New Application" 버튼 클릭
   - 애플리케이션 이름 입력 (예: "핫딜 봇")
   - "Create" 클릭

3. **봇 생성**
   - 왼쪽 메뉴에서 "Bot" 선택
   - "Add Bot" 버튼 클릭
   - "Yes, do it!" 클릭하여 확인

4. **봇 토큰 발급**
   - "Token" 섹션에서 "Reset Token" 또는 "Copy" 클릭
   - **중요**: 토큰을 안전하게 복사하여 저장 (다시 볼 수 없음)
   - 토큰을 `.env` 파일의 `DISCORD_TOKEN`에 설정

5. **Privileged Gateway Intents 설정**
   - "Privileged Gateway Intents" 섹션에서 다음 옵션 활성화:
     - ✅ **MESSAGE CONTENT INTENT** (필수)
       - 메시지 내용을 읽기 위해 필요
   - "Save Changes" 클릭

6. **봇 초대 URL 생성**
   - 왼쪽 메뉴에서 "OAuth2" → "URL Generator" 선택
   - "Scopes" 섹션에서 다음 선택:
     - ✅ `bot`
     - ✅ `applications.commands` (슬래시 명령어 사용 시)
   - "Bot Permissions" 섹션에서 필요한 권한 선택:
     - ✅ `Send Messages` (메시지 전송)
     - ✅ `Read Message History` (메시지 읽기)
     - ✅ `Use Slash Commands` (슬래시 명령어)
     - ✅ `Embed Links` (임베드 메시지)
   - 하단에 생성된 URL을 복사
   - 브라우저에서 해당 URL을 열어 봇을 서버에 초대

### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 봇 토큰을 설정하세요:

```bash
# Discord 봇 토큰 (필수)
DISCORD_TOKEN=your_bot_token_here

# 나머지 설정...
```

### 3. 봇 권한 확인

봇이 정상 작동하려면 다음 권한이 필요합니다:
- **텍스트 메시지 읽기**: 채널의 메시지를 읽기 위해 필요
- **텍스트 메시지 전송**: 명령어 응답 및 알림 전송에 필요
- **임베드 링크**: Embed 형식 메시지 전송에 필요
- **DM 전송**: 개인 메시지 알림 전송에 필요

### 4. 봇 초대 방법

1. **OAuth2 URL Generator 사용** (권장)
   - 위의 "봇 초대 URL 생성" 단계에서 생성한 URL 사용
   - URL을 브라우저에서 열면 Discord가 봇을 초대할 서버를 선택하도록 요청
   - 서버 선택 후 권한 확인 및 승인

2. **수동 초대**
   - Discord 서버 설정 → 연동 → 봇 추가
   - Discord Developer Portal에서 봇을 검색하여 추가
   - 필요한 권한 선택 후 승인

### 5. 봇 상태 확인

봇이 정상적으로 작동하는지 확인:

```bash
# 봇 실행
python bot.py

# 또는 Docker로 실행
docker-compose up -d
```

봇이 온라인 상태로 표시되고, Discord 서버에서 `!ping` 명령어로 테스트할 수 있습니다.

## 주의사항

- **Discord 봇 토큰 보안**
  - 봇 토큰은 절대 공개 저장소에 커밋하지 마세요
  - `.env` 파일은 `.gitignore`에 추가되어 있어야 합니다
  - 토큰이 유출되면 즉시 Discord Developer Portal에서 토큰을 재설정하세요

- **필수 설정**
  - **MESSAGE CONTENT INTENT**를 반드시 활성화해야 합니다
  - 이 Intent가 없으면 봇이 메시지 내용을 읽을 수 없습니다

- **봇 제한사항**
  - 봇은 Discord API Rate Limit을 준수해야 합니다
  - 과도한 요청 시 일시적으로 차단될 수 있습니다

## 라이선스

MIT
