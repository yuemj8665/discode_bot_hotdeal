# Hotdeal Bot ArgoCD 배포 가이드

## 사전 준비

### 1. Secret 설정

Discord 봇 토큰을 Kubernetes Secret으로 설정해야 합니다:

```bash
# Secret 생성 (실제 토큰으로 변경)
kubectl create secret generic dev-hotdeal-bot-secret \
  -n hotdeal-bot-dev \
  --from-literal=DISCORD_TOKEN='YOUR_ACTUAL_DISCORD_TOKEN'

# 또는 기존 Secret 업데이트
kubectl create secret generic dev-hotdeal-bot-secret \
  -n hotdeal-bot-dev \
  --from-literal=DISCORD_TOKEN='YOUR_ACTUAL_DISCORD_TOKEN' \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 2. PostgreSQL 서비스 설정

데이터베이스 연결을 위해 PostgreSQL 서비스가 필요합니다:

**옵션 1: 외부 PostgreSQL 사용**
- ConfigMap의 `DATABASE_URL`을 외부 PostgreSQL 주소로 수정

**옵션 2: Kubernetes 내부 PostgreSQL 배포**
- PostgreSQL Deployment와 Service를 별도로 생성

### 3. GitHub 저장소 설정

`argocd/application.yaml`의 `repoURL`을 실제 GitHub 저장소 URL로 수정:

```yaml
source:
  repoURL: https://github.com/YOUR_USERNAME/discode_bot_hotdeal.git
```

## ArgoCD Application 등록

```bash
# 프로젝트 디렉토리로 이동
cd /Users/mamyeongjae/home-server/workspace/personal/discode_bot_hotdeal

# ArgoCD Application 등록
kubectl apply -f argocd/application.yaml

# 등록 확인
kubectl get applications -n argocd

# Application 상태 확인
kubectl get application hotdeal-bot-dev -n argocd
```

## 배포 상태 확인

```bash
# Pod 상태 확인
kubectl get pods -n hotdeal-bot-dev

# Pod 로그 확인
kubectl logs -f deployment/dev-hotdeal-bot -n hotdeal-bot-dev

# Deployment 상태 확인
kubectl get deployment -n hotdeal-bot-dev
```

## 자동 배포

```bash
# 배포 스크립트 실행
./deploy.sh "커밋 메시지"

# 또는 직접 실행
docker build -t hotdeal-bot:$(date +%Y%m%d_%H%M) .
# kustomization.yaml 수정
git add . && git commit -m "Deploy" && git push
```

## 주의사항

1. **헬스체크 없음**: Discord 봇은 HTTP 서버가 아니므로 liveness/readiness probe를 제거했습니다.
2. **Secret 관리**: Discord 토큰은 반드시 Secret으로 관리하고 Git에 커밋하지 마세요.
3. **데이터베이스 연결**: PostgreSQL 서비스가 네임스페이스 내에 있어야 합니다.
4. **이미지 빌드**: 로컬에서 빌드한 이미지는 Kubernetes에서 접근할 수 없으므로, 이미지 레지스트리 사용을 권장합니다.

## 문제 해결

### Pod가 시작되지 않음

```bash
# Pod 이벤트 확인
kubectl describe pod <pod-name> -n hotdeal-bot-dev

# 로그 확인
kubectl logs <pod-name> -n hotdeal-bot-dev
```

### Secret 오류

```bash
# Secret 확인
kubectl get secret dev-hotdeal-bot-secret -n hotdeal-bot-dev

# Secret 재생성
kubectl delete secret dev-hotdeal-bot-secret -n hotdeal-bot-dev
kubectl create secret generic dev-hotdeal-bot-secret \
  -n hotdeal-bot-dev \
  --from-literal=DISCORD_TOKEN='YOUR_TOKEN'
```

### 데이터베이스 연결 실패

```bash
# ConfigMap 확인
kubectl get configmap dev-hotdeal-bot-config -n hotdeal-bot-dev -o yaml

# DATABASE_URL 수정
kubectl edit configmap dev-hotdeal-bot-config -n hotdeal-bot-dev
```
