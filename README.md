# Aggregator API

スポット測定データを統合し、LLM分析用プロンプトを生成するFastAPI

## 概要

**役割**: spot_featuresテーブルから3つの特徴抽出結果を取得し、観測対象者情報と時間コンテキストを統合してLLM用プロンプトを生成

**入力**: (device_id, recorded_at)
**出力**: spot_aggregators.aggregated_prompt

---

## エンドポイント

### 1. ヘルスチェック
GET /health

### 2. スポット測定プロンプト生成
POST /aggregator/spot

---

## ローカル開発

### 環境変数の設定
cp .env.example .env

### Docker起動
docker-compose up --build

### 動作確認
curl http://localhost:8050/health

---

## デプロイ

### EC2に接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

### デプロイ実行
cd /home/ubuntu/aggregator
./run-prod.sh

---

**最終更新**: 2025-11-11
# Deploy test 2025年 11月11日 火曜日 14時20分52秒 JST
