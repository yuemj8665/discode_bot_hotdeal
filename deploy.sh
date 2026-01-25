#!/bin/bash

set -e

# 설정 - 프로젝트에 맞게 수정
IMAGE_NAME="hotdeal-bot"
KUSTOMIZATION_PATH="k8s/overlays/dev/kustomization.yaml"

# 태그 생성
TAG=$(date +%Y%m%d_%H%M)
COMMIT_MSG="${1:-Deploy version $TAG}"

echo "=========================================="
echo "  배포 시작: ${IMAGE_NAME}:${TAG}"
echo "=========================================="

# 1. Docker 빌드
echo "[1/4] Docker 빌드..."
docker build -t ${IMAGE_NAME}:${TAG} .

# 2. kustomization.yaml 업데이트
echo "[2/4] 이미지 태그 업데이트..."
sed -i '' "s/newTag: .*/newTag: \"${TAG}\"/" ${KUSTOMIZATION_PATH}

# 3. Git 커밋 & 푸시
echo "[3/4] Git 커밋..."
git add .
git commit -m "$COMMIT_MSG"

echo "[4/4] Git 푸시..."
git push

echo "=========================================="
echo "  배포 완료: ${IMAGE_NAME}:${TAG}"
echo "  ArgoCD가 자동으로 배포합니다."
echo "=========================================="
