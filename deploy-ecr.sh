#!/bin/bash

# ECR設定
ECR_REGISTRY="754724220380.dkr.ecr.ap-southeast-2.amazonaws.com"
ECR_REPOSITORY="watchme-aggregator"
IMAGE_TAG="latest"
REGION="ap-southeast-2"

# カラー出力設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Aggregator API - ECRデプロイ開始${NC}"
echo "=================================="

# 1. ECRにログイン
echo -e "\n${YELLOW}📝 ECRにログイン中...${NC}"
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ECRログインに失敗しました${NC}"
    exit 1
fi
echo -e "${GREEN}✅ ECRログイン成功${NC}"

# 2. Dockerイメージのビルド
echo -e "\n${YELLOW}🔨 Dockerイメージをビルド中...${NC}"
docker build -f Dockerfile.prod -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Dockerビルドに失敗しました${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Dockerビルド成功${NC}"

# 3. イメージにタグ付け
echo -e "\n${YELLOW}🏷️  イメージにタグ付け中...${NC}"
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ タグ付けに失敗しました${NC}"
    exit 1
fi
echo -e "${GREEN}✅ タグ付け成功${NC}"

# 4. ECRにプッシュ
echo -e "\n${YELLOW}📤 ECRにイメージをプッシュ中...${NC}"
docker push ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ECRプッシュに失敗しました${NC}"
    exit 1
fi
echo -e "${GREEN}✅ ECRプッシュ成功${NC}"

# 5. デプロイ完了
echo -e "\n${GREEN}=================================="
echo -e "🎉 デプロイが正常に完了しました！"
echo -e "==================================\n"
echo -e "イメージURI: ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"
echo -e "\n次のステップ:"
echo -e "1. EC2サーバーにSSH接続"
echo -e "   ${YELLOW}ssh -i ~/watchme-key.pem ubuntu@3.24.16.82${NC}"
echo -e "2. 最新イメージをプル"
echo -e "   ${YELLOW}docker pull ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}${NC}"
echo -e "3. コンテナを再起動"
echo -e "   ${YELLOW}cd /home/ubuntu/aggregator${NC}"
echo -e "   ${YELLOW}docker-compose -f docker-compose.prod.yml down${NC}"
echo -e "   ${YELLOW}docker-compose -f docker-compose.prod.yml up -d${NC}"
