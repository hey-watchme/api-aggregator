# Aggregator API

スポット測定データを統合し、**タイムライン同期型**LLM分析用プロンプトを生成するFastAPI

---

## 概要

**役割**: spot_featuresテーブルから3つの特徴抽出結果（ASR + SED + SER）を取得し、時系列を保持した統合プロンプトを生成

**プロンプト形式**: タイムライン同期型（10秒ごとにSED/SERを同期表示）

**アーキテクチャ**: UTC統一アーキテクチャ（全タイムスタンプをUTCで保存、表示時にローカル時間変換）

**入力**: (device_id, recorded_at)
**出力**: spot_aggregators.prompt（~4000文字）

---

## 🎯 新プロンプトフォーマット（Timeline-Synchronized）

### 主な特徴

1. **Full Transcription（全文）**: 時系列なし、全体で1つのテキスト
2. **Timeline（10秒ごと同期）**: SED（音響イベント）+ SER（感情）を同じ時間軸で表示
3. **Pattern Detection**: 自動的に「笑い声 + 喜び」「衝突音 + 怒り」などを検出
4. **Overall Summary**: 統計情報とキーパターン

### プロンプト構造例

```markdown
# Full Transcription (60 seconds)
ちしても良くないけどもしばんなどんばい...

# Acoustic & Emotional Timeline (10-second synchronized analysis)

## 0-10秒
**Behavior Analysis (SED):**
  - Speech / 会話・発話: 76.5% (high confidence)
  - Child speech / 子供の声: 15.7% (low confidence)

**Emotion Analysis (SER):**
  - Primary: 喜び (Score: 3.46)
  - All emotions: 喜び(3.46), 中立(0.81), 悲しみ(-1.17), 怒り(-2.45)

**Pattern:** 会話中、喜びの感情

---

## 10-20秒
**Behavior Analysis (SED):**
  - Speech / 会話・発話: 55.8% (medium confidence)

**Emotion Analysis (SER):**
  - Primary: 喜び (Score: 5.19)  ← 感情が高揚

**Pattern:** 会話中、喜びの感情

---

# Overall Summary
- **Duration:** 60 seconds
- **Speech Activity:** Average 71.1%, Peak 86.4% at 40-50s
- **Emotion Trend:** 喜び (dominant), Range: 2.70-5.19, Peak: 10s
- **Emotion Timeline:** 喜び → 喜び → 喜び → 喜び → 喜び → 喜び
```

### 時系列保持の効果

**シーン例: 怒って物を投げた**
```markdown
## 10-20秒
**Behavior Analysis (SED):**
  - Crash / 衝突音: 68.5% (high confidence)  ← 物を投げた音
  - Glass breaking / ガラス破損: 22.1%

**Emotion Analysis (SER):**
  - Primary: 怒り (Score: 5.89)  ← 高い怒りスコア

**Pattern:** 衝突音 + 怒りの感情 → 物を投げた可能性が高い

## 20-30秒（直後）
**Behavior Analysis (SED):**
  - Silence / 静寂: 78.3%  ← 急に静かになった

**Emotion Analysis (SER):**
  - Primary: 悲しみ (Score: 4.21)  ← 怒り→悲しみに変化

**Pattern:** 怒りの後、静寂と悲しみ → 後悔・落ち着きのフェーズ
```

→ LLMが「10-20sで怒りと衝突音が同時発生。直後に静寂と悲しみ。感情の変化が物を投げた行動と整合している」と判断可能

---

## データフロー

```
1. spot_features から3つの特徴データ取得
   - vibe_transcriber_result (ASR: 文字起こし) - 時系列なし
   - behavior_extractor_result (SED: 音響イベント) - 10秒ブロック
   - emotion_extractor_result (SER: 感情) - 10秒チャンク

2. devices.timezone 取得

3. UTC → ローカル時間変換（pytz使用）

4. 時間コンテキスト生成
   - 季節、曜日、時間帯、祝日

5. subject_info 取得（年齢、性別、メモ）

6. タイムライン統合プロンプト生成（~4000文字）
   - Full Transcription
   - Timeline (10-second blocks): SED + SER 同期表示
   - Pattern detection: 自動相関検出
   - Overall Summary: 統計とキーパターン

7. spot_aggregators テーブルに保存
   - prompt: タイムライン統合プロンプト
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
  "aggregated_prompt": "# Spot Recording Analysis Task\n\n...\n\n# Full Transcription (60 seconds)\n\n...\n\n# Acoustic & Emotional Timeline (10-second synchronized analysis)\n\n## 0-10秒\n**Behavior Analysis (SED):**\n  - Speech / 会話・発話: 76.5% (high confidence)\n\n**Emotion Analysis (SER):**\n  - Primary: 喜び (Score: 3.46)\n\n**Pattern:** 会話中、喜びの感情\n\n---\n\n...",
  "context_data": {
    "has_transcription": true,
    "has_behavior_data": true,
    "has_emotion_data": true,
    "has_subject_info": true,
    "subject_age": 5,
    "subject_gender": "男性"
  },
  "message": "Spot aggregation completed successfully"
}
```

**プロンプト内容** (aggregated_prompt):
- Task Definition & Guidelines: ~2500文字
- Temporal Context: ~200文字
- Full Transcription: 100-500文字（可変）
- Timeline (6 blocks × 150文字): ~900文字
- Overall Summary: ~400文字
- **合計**: ~4000文字

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

## 変更履歴

### 2025-11-12 - Timeline-Synchronized Format 🎉

**目的**: 時系列の文脈を保持し、LLM分析の精度向上

**変更内容**:
1. **プロンプト形式を全面刷新**
   - 旧: ASR/SED/SERが別々のセクション
   - 新: 10秒ごとにSED+SERを同期表示（タイムライン型）

2. **技術名の汎用化**
   - SED (Sound Event Detection)
   - SER (Speech Emotion Recognition)

3. **パターン検出機能追加**
   - 自動的に「笑い声 + 喜び」「衝突音 + 怒り」を検出
   - LLMが時間軸で感情と行動の相関を理解可能

**効果**:
- 「怒って物を投げた」のような複雑なシーンを正確に分析可能
- 感情の変化（喜び→怒り→悲しみ）を時系列で追跡
- プロンプト長: 5000文字 → 4000文字（20%削減）

**修正ファイル**:
- `services/prompt_generator.py`: 全面書き換え
- `services/data_fetcher.py`: データ構造の修正

---

**最終更新**: 2025-11-12
**ステータス**: ✅ 本番稼働中（Timeline-Synchronized Format）
