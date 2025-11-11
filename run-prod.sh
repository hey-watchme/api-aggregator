#!/bin/bash

# ECR設定
ECR_REGISTRY="754724220380.dkr.ecr.ap-southeast-2.amazonaws.com"
ECR_REPOSITORY="watchme-aggregator"
IMAGE_TAG="latest"
REGION="ap-southeast-2"

# カラー出力設定
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Aggregator API - 本番デプロイ${NC}"
echo "=================================="

# 1. ECRにログイン
echo -e "\n${YELLOW}📝 ECRにログイン中...${NC}"
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# 2. 最新イメージをプル
echo -e "\n${YELLOW}📥 最新イメージをプル中...${NC}"
docker pull ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}

# 3. 既存のコンテナを停止
echo -e "\n${YELLOW}⏹️  既存のコンテナを停止中...${NC}"
docker-compose -f docker-compose.prod.yml down

# 4. 新しいコンテナを起動
echo -e "\n${YELLOW}▶️  新しいコンテナを起動中...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# 5. ヘルスチェック
echo -e "\n${YELLOW}🔍 ヘルスチェック中...${NC}"
sleep 5
curl -f http://localhost:8050/health
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ ヘルスチェック成功${NC}"
else
    echo -e "\n${RED}❌ ヘルスチェック失敗${NC}"
    docker logs aggregator-api --tail 50
fi

# 6. コンテナ状態確認
echo -e "\n${YELLOW}📊 コンテナ状態:${NC}"
docker ps | grep aggregator-api

echo -e "\n${GREEN}✨ デプロイ完了${NC}"
