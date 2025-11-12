# Aggregator API

スポット測定データを統合し、LLM分析用プロンプトを生成するFastAPI

---

## 概要

**役割**: spot_featuresテーブルから3つの特徴抽出結果を取得し、観測対象者情報と時間コンテキストを統合してLLM用プロンプトを生成

**アーキテクチャ**: UTC統一アーキテクチャ（全タイムスタンプをUTCで保存、表示時にローカル時間変換）

**入力**: (device_id, recorded_at)
**出力**: spot_aggregators.prompt

---

## データフロー

```
1. spot_features から3つの特徴データ取得
   - vibe_transcriber_result (ASR: 文字起こし)
   - behavior_extractor_result (SED: 音響イベント)
   - emotion_extractor_result (SER: 感情)

2. devices.timezone 取得

3. UTC → ローカル時間変換（pytz使用）

4. 時間コンテキスト生成
   - 季節、曜日、時間帯、祝日

5. subject_info 取得（年齢、性別、メモ）

6. LLM用プロンプト生成（4700文字程度）

7. spot_aggregators テーブルに保存
   - prompt: LLM分析用統合プロンプト
   - context_data: メタデータ（JSONB）
```

---

## エンドポイント

### 1. ヘルスチェック
```bash
GET /health
```

**レスポンス例**:
```json
{
  "status": "healthy",
  "service": "aggregator-api"
}
```

---

### 2. スポット測定プロンプト生成
```bash
POST /aggregator/spot
```

**リクエストボディ**:
```json
{
  "device_id": "9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93",
  "recorded_at": "2025-11-12 08:31:01.473+00"
}
```

**レスポンス例**:
```json
{
  "status": "success",
  "device_id": "9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93",
  "recorded_at": "2025-11-12 08:31:01.473+00",
  "timezone": "Asia/Tokyo",
  "aggregated_prompt": "# Spot Recording Analysis Task\n\nAnalyze...",
  "context_data": {
    "has_transcription": true,
    "has_behavior_data": false,
    "has_emotion_data": false,
    "has_subject_info": true,
    "subject_age": 5,
    "subject_gender": "男性"
  },
  "message": "Spot aggregation completed successfully"
}
```

---

## 本番環境

### URL
- **外部**: https://api.hey-watch.me/aggregator/
- **内部**: http://localhost:8050/

### テスト方法
```bash
# ヘルスチェック
curl https://api.hey-watch.me/health

# スポット測定プロンプト生成
curl -X POST https://api.hey-watch.me/aggregator/spot \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93",
    "recorded_at": "2025-11-12 08:31:01.473+00"
  }'
```

---

## ローカル開発

### 環境変数の設定
```bash
cp .env.example .env
# 以下を設定
# SUPABASE_URL=your_supabase_url
# SUPABASE_KEY=your_supabase_key
```

### Docker起動
```bash
docker-compose up --build
```

### 動作確認
```bash
# ヘルスチェック
curl http://localhost:8050/health

# スポット測定プロンプト生成
curl -X POST http://localhost:8050/aggregator/spot \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device-id",
    "recorded_at": "2025-11-12T08:31:01.473Z"
  }'
```

---

## デプロイ

### 自動デプロイ（推奨）
```bash
# mainブランチにpushすると自動デプロイ
git add .
git commit -m "update: description"
git push origin main
```

GitHub Actionsが自動的に以下を実行：
1. Dockerイメージビルド
2. ECRへpush
3. EC2でコンテナ再起動

### 手動デプロイ（緊急時のみ）
```bash
# EC2に接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# デプロイ実行
cd /home/ubuntu/aggregator
./run-prod.sh
```

---

## データベーススキーマ

### spot_aggregators テーブル

```sql
CREATE TABLE spot_aggregators (
  device_id TEXT NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL,  -- UTC
  prompt TEXT NOT NULL,               -- LLM分析用統合プロンプト
  context_data JSONB,                 -- メタデータ
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (device_id, recorded_at)
);
```

**RLS**: 無効（内部API専用テーブル）

---

## トラブルシューティング

### 問題: 404 Not Found

**原因**: Nginx設定のproxy_passが間違っている

**確認**:
```bash
ssh ubuntu@3.24.16.82
sudo grep -A 5 "location /aggregator/" /etc/nginx/sites-available/api.hey-watch.me
```

**正しい設定**:
```nginx
location /aggregator/ {
    proxy_pass http://localhost:8050/aggregator/;  # /aggregator/ を残す
}
```

---

### 問題: RLSエラー

**症状**: `new row violates row-level security policy`

**解決方法**:
```sql
-- Supabase SQL Editor で実行
ALTER TABLE spot_aggregators DISABLE ROW LEVEL SECURITY;
```

---

### 問題: 環境変数が見つからない

**確認**:
```bash
ssh ubuntu@3.24.16.82
cat /home/ubuntu/aggregator/.env
```

**必須環境変数**:
- SUPABASE_URL
- SUPABASE_KEY

---

## 技術スタック

- **Framework**: FastAPI 0.104.1
- **Database**: Supabase (PostgreSQL)
- **Timezone**: pytz 2024.1
- **Container**: Docker (ARM64)
- **CI/CD**: GitHub Actions → ECR → EC2
- **Port**: 8050

---

**最終更新**: 2025-11-12
**ステータス**: ✅ 本番稼働中
