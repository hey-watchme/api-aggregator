# Aggregator API

スポット測定データを統合し、**タイムライン同期型**LLM分析用プロンプトを生成するFastAPI

---

## 概要

**役割**: spot_featuresテーブルから3つの特徴抽出結果（ASR + SED + SER）を取得し、時系列を保持した統合プロンプトを生成

**プロンプト形式**: 統合タイムライン型（5秒ブロックでASR・SED・SERを時間同期）

**アーキテクチャ**: UTC統一アーキテクチャ（全タイムスタンプをUTCで保存、表示時にローカル時間変換）

**入力**: (device_id, recorded_at)
**出力**: spot_aggregators.prompt（~4000文字）

---

## 🗺️ ルーティング詳細

| 項目 | 値 | 説明 |
|------|-----|------|
| **🏷️ サービス名** | Aggregator API | スポット測定データ統合・プロンプト生成 |
| **📊 役割** | データ統合 | ASR + SED + SER → LLM分析用プロンプト |
| | | |
| **🌐 外部アクセス（Nginx）** | | |
| └ 公開エンドポイント | `https://api.hey-watch.me/aggregator/` | 外部からのアクセスパス |
| └ Nginx設定ファイル | `/etc/nginx/sites-available/api.hey-watch.me` | |
| └ proxy_pass先 | `http://localhost:8050/aggregator/` | 内部転送先 |
| └ タイムアウト | 180秒 | read/connect/send |
| | | |
| **🔌 API内部エンドポイント** | | |
| └ ヘルスチェック | `/health` | GET |
| └ **スポット統合** | `/aggregator/spot` | POST - プロンプト生成 |
| └ **デイリー統合** | `/aggregator/daily` | POST - 日次プロンプト生成 |
| └ **ウィークリー統合** | `/aggregator/weekly` | POST - 週次プロンプト生成 (試験段階) |
| | | |
| **🐳 Docker/コンテナ** | | |
| └ コンテナ名 | `aggregator-api` | ✅ 統一命名規則 |
| └ ポート（内部） | 8050 | コンテナ内 |
| └ ポート（公開） | `127.0.0.1:8050:8050` | ローカルホストのみ |
| └ ヘルスチェック | `/health` | Docker healthcheck |
| | | |
| **☁️ AWS ECR** | | |
| └ リポジトリ名 | `watchme-aggregator` | ✅ ECRリポジトリ |
| └ リージョン | ap-southeast-2 (Sydney) | |
| └ URI | `754724220380.dkr.ecr.ap-southeast-2.amazonaws.com/watchme-aggregator:latest` | |
| | | |
| **📂 ディレクトリ** | | |
| └ ソースコード | `/Users/kaya.matsumoto/projects/watchme/api/aggregator` | ローカル |
| └ GitHubリポジトリ | `hey-watchme/api-aggregator` | |
| └ EC2配置場所 | `/home/ubuntu/aggregator` | 本番実行ディレクトリ |
| | | |
| **🔗 呼び出し元** | | |
| └ Lambda関数 | `watchme-audio-worker` | 特徴抽出完了後に自動呼び出し |
| └ 呼び出しURL | `https://api.hey-watch.me/aggregator/spot` | フルパス |
| └ 環境変数 | `API_BASE_URL=https://api.hey-watch.me` | Lambda内 |
| | | |
| **📥 データソース** | | |
| └ 入力テーブル | `spot_features` | ASR + SED + SERの特徴データ |
| └ 参照テーブル | `devices` (timezone), `subjects` (年齢・性別) | メタデータ |
| └ 出力テーブル | `spot_aggregators`, `daily_aggregators`, `weekly_aggregators` | 統合プロンプト（TEXT） |

---

## 🎯 プロンプトフォーマット

### 設計思想：統合タイムライン（Unified Timeline）

**3つの分析結果を同一の時間軸で同期表示する**ことが最大の特徴。

従来は ASR（文字起こし）、SED（音響イベント）、SER（感情分析）が**それぞれ別セクション・別の時間単位**で表示されていた。
これを **5秒ブロック** に統一し、「その5秒間に何が話され、どんな音が鳴り、どんな感情だったか」を一目で把握できるようにした。

**統合の根拠**:
- ASR: Speechmatics APIから**単語ごとのタイムスタンプ**（`start_time`, `end_time`）を取得し、5秒ブロックに割り当て
- SED: 1秒間隔のイベントデータを5秒ブロックに集約（各ブロック内の最大スコアを採用）
- SER: Hume AIの発話区間ベースのセグメント（可変長）を、時間が重なる5秒ブロックに割り当て

**データ優先順位**:
1. **ASR**: PRIMARY SOURCE - 最も信頼できる会話内容
2. **SED**: RELIABLE CONTEXT - 会話を補完する音響イベント
3. **SER**: REFERENCE - 精度が低いため補助的に使用

### 主な特徴

1. **Counselor Role**: セッションノートを書くように、THIS recordingに焦点
2. **Unified Timeline（5秒ブロック同期）**: ASR + SED + SER を同じ時間軸で統合表示
3. **話者分離**: ASRが話者ラベル（S1, S2...）付きで表示されるため、誰が何を言ったかが明確
4. **レガシー互換**: `words` データがない旧録音は従来形式（分離表示）にフォールバック

### 出力フォーマット

```json
{
  "summary": "この録音で観察されたことを2-3文で記述（日本語）",
  "vibe_score": 45,
  "behavior": "会話, 食事, 家族団らん"
}
```

### Vibe Score計算方式

**Summary-Based Scoring（Summaryから逆算）**:
1. Summaryの内容を読んで基礎スコア決定（-60〜+60）
2. 時間帯・会話エンゲージメントで補正（-20〜+20）
3. SER（感情スコア）で段階的調整（-15〜+15）
   - Strong signals (≥4.0): 必ず参考（±10〜±15）
   - Moderate signals (2.0-4.0): Summaryと一致すれば使用（±5〜±10）
   - Weak signals (<2.0): 無視

**特別処理**:
- "発話なし" + SED Speech検出 = 会話はあったが内容不明と解釈
- Base +5〜+10に設定（完全な沈黙ではない）
- SERが強ければ追加ボーナス

**スコアレンジ**:
- Highly Positive (40-60): 楽しい遊び、学習、褒められる
- Positive (20-40): 日常的な会話、食事、穏やかな時間
- Neutral (-20 to +20): 背景会話、受動的活動
- Negative (-40 to -20): 不満、軽い衝突、不快感
- Highly Negative (-60 to -40): 激しい泣き、喧嘩、苦痛

**計算例**:
```
発話なし + Speech 0.75 + Joy 4.6
= 8 (base) + 5 (time) + 10 (speech) + 12 (joy)
= 35
```

### プロンプト構造例（統合タイムライン形式）

```markdown
# Spot Recording Analysis Task
You are a professional counselor writing a brief session note...

# Output Format
(JSON: summary, vibe_score, behavior, emotion, rating)

# Recording Context
Duration: 60 seconds / Date: 2026-03-08 / Local Time: 21:30 (夜)

# Unified Analysis Timeline (5s blocks)

## 0-5s
  ASR [S1]: "あれね。あそこかと。"
  SED: Speech(65%), Background noise(12%)
  SER [1.7-4.0s]: 困惑(0.24) | 困惑(0.24), 驚き(0.14), 怒り(0.09)

## 5-10s
  ASR [S1]: "10888多そう。816。あ。"
  ASR [S2]: "3ぞすぐわかった。"
  SED: Speech(77%)
  SER [5.1-5.7s]: 穏やかさ(0.12) | 穏やかさ(0.12), 困惑(0.10), 関心(0.07)
  SER [6.5-7.2s]: 悲しみ(0.14) | 悲しみ(0.14), 穏やかさ(0.09), 苦悩(0.08)

## 15-20s
  SED: Speech(60%)
  SER(burst) [16.0-17.0s]: 気まずさ(0.35)

## Overall Text Emotion (language analysis)
  Dominant: 熱意(0.45)
  Top 5: 熱意(0.45), 興奮(0.38), 関心(0.18), 満足感(0.16), 喜び(0.15)

# Analysis Process
(Step 1: Summary, Step 2: Vibe Score, Step 3: Emotions)
```

### 統合タイムラインの効果

**シーン例: 怒って物を投げた**
```markdown
## 10-15s
  ASR [S1]: "やめてよ！もう嫌！"
  SED: Crash(69%), Speech(55%)
  SER [10.2-12.5s]: 怒り(0.58) | 怒り(0.58), 苛立ち(0.32), 苦悩(0.21)

## 15-20s
  SED: Silence(78%)
  SER [15.0-18.0s]: 悲しみ(0.42) | 悲しみ(0.42), 羞恥(0.18), 罪悪感(0.15)
```

→ LLMが**同一タイムライン上で**「発話内容 + 衝突音 + 怒り」→「静寂 + 悲しみ」という感情遷移を読み取れる

---

## データフロー

```
1. spot_features から3つの特徴データ取得
   - vibe_transcriber_result (ASR: jsonb)
     - transcription: 話者ラベル付きテキスト
     - words: 単語ごとのタイムスタンプ・話者・信頼度
   - behavior_extractor_result (SED: jsonb) - 1秒間隔イベント
   - emotion_features_result_hume (SER: jsonb) - 発話区間ベース48感情

2. devices.timezone 取得

3. UTC → ローカル時間変換（pytz使用）

4. 時間コンテキスト生成（季節、曜日、時間帯、祝日）

5. subject_info 取得（年齢、性別、メモ）

6. 統合タイムライン生成
   - ASR words を 5秒ブロックに割り当て（話者別グルーピング）
   - SED 1秒イベントを 5秒ブロックに集約（最大スコア採用、上位3件）
   - SER prosody/burst セグメントを時間重複する 5秒ブロックに配置
   - language分析（テキスト全体）は別枠で表示

7. spot_aggregators テーブルに保存
   - prompt: 統合タイムラインプロンプト
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
- Task Definition & Output Format: ~2500文字
- Recording Context: ~200文字
- Unified Analysis Timeline（5秒ブロック × 最大12-17ブロック）: ~1500文字
- Analysis Guidelines: ~500文字
- **合計**: ~4500文字

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

## 📅 Weekly Aggregator ✅ (試験段階)

### 概要

**実装日**: 2025-11-19
**ステータス**: ✅ 実装済み - **試験段階（アプリ・ワークフロー未統合）**

週次（月曜〜日曜）の録音データから印象的な出来事5件を選出するためのプロンプトを生成。

### エンドポイント

```bash
curl -X POST https://api.hey-watch.me/aggregator/weekly \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93",
    "week_start_date": "2025-11-10"
  }'
```

**パラメータ**:
- `device_id`: デバイスID
- `week_start_date`: 週の開始日（月曜日、YYYY-MM-DD形式）

### データフロー

```
spot_features (vibe_transcriber_result)
    ↓
1週間分（月曜〜日曜）の発話内容を取得
    ↓
Weekly Aggregator: プロンプト生成
    ↓
weekly_aggregators テーブルに保存
    ↓
(手動実行) Profiler API: /weekly-profiler
    ↓
weekly_results テーブルに保存
```

### 週の定義

**月曜始まり（ISO 8601準拠）**:
- 週の開始: 月曜日 00:00
- 週の終了: 日曜日 23:59
- `week_start_date`: 必ず月曜日の日付（YYYY-MM-DD）

**実装箇所**:
- `endpoints/weekly_aggregator.py` の `get_week_end_date()` 関数
- ロジック: `week_start_date + 6日 = week_end_date`（日曜日）

### 更新タイミングの想定

**毎日更新方式**:
- 毎日日付が変わった際（00:00）に前日の日付を含む週のデータを再処理
- 週の途中でも常に最新のweekly dataが閲覧可能
- 例: 水曜日の場合
  - 対象週: 月曜〜日曜（月〜水のデータのみ存在）
  - 翌日（木曜）に再実行 → 月〜木のデータで更新
  - 日曜まで毎日更新 → 週が完成

**データ取得ロジック**:
```sql
-- spot_features から local_date で範囲取得
WHERE device_id = ?
  AND local_date >= '2025-11-17'  -- Monday
  AND local_date <= '2025-11-23'  -- Sunday
```

### 処理フロー

1. `spot_features`から1週間分（月曜〜日曜）のデータを取得
2. `vibe_transcriber_result`（発話内容）を時系列で整理
3. LLMに「印象的なイベント5件を選出」するプロンプトを生成
4. `weekly_aggregators`テーブルに保存（UPSERT - 既存データは上書き）

### 出力データ構造

**weekly_aggregators テーブル**:
```sql
CREATE TABLE weekly_aggregators (
  device_id TEXT NOT NULL,
  week_start_date DATE NOT NULL,  -- 月曜日
  prompt TEXT NOT NULL,            -- LLM用プロンプト
  context_data JSONB,              -- メタデータ
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (device_id, week_start_date)
);
```

**context_data 例**:
```json
{
  "week_range": "2025-11-10 - 2025-11-16",
  "week_start_date": "2025-11-10",
  "week_end_date": "2025-11-16",
  "spot_count": 60,
  "recording_times": ["2025-11-14T21:01:01.759+00:00", ...]
}
```

### プロンプト内容

- タスク: 1週間の録音データから印象的なイベント5件を選出
- 選出基準:
  - 興味深い会話内容
  - 記憶に残る出来事
  - 週全体の多様性を考慮
- 出力形式: JSON（rank、date、time、day_of_week、event_summary、transcription_snippet）

### レスポンス例

```json
{
  "status": "success",
  "device_id": "9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93",
  "week_start_date": "2025-11-10",
  "week_end_date": "2025-11-16",
  "spot_count": 60,
  "aggregated_prompt": "# Weekly Memorable Events Selection Task...",
  "context_data": {
    "week_range": "2025-11-10 - 2025-11-16",
    "spot_count": 60
  },
  "message": "Weekly aggregation completed successfully for 2025-11-10 to 2025-11-16"
}
```

### 自動実行の想定（未実装）

**将来の自動化案**:
1. **Lambda関数**: 毎日 00:00 に実行
2. **処理内容**:
   ```python
   # 前日の日付を含む週の月曜日を計算
   yesterday = today - timedelta(days=1)
   week_monday = yesterday - timedelta(days=yesterday.weekday())

   # Weekly Aggregator API呼び出し
   POST /aggregator/weekly
   {
     "device_id": "...",
     "week_start_date": week_monday  # YYYY-MM-DD (Monday)
   }

   # Weekly Profiler API呼び出し
   POST /profiler/weekly-profiler
   {
     "device_id": "...",
     "week_start_date": week_monday
   }
   ```
3. **結果**: 週の途中でも毎日最新データに更新

### 注意事項

⚠️ **現在は試験段階**:
- アプリのワークフローには未統合
- 手動でAPIを呼び出してテスト可能
- Lambda自動トリガーなし（上記の自動化案は未実装）
- 今後の機能拡張で本番導入予定

### 関連エンドポイント

- **Profiler API**: `/profiler/weekly-profiler` - LLM分析実行（weekly_aggregatorsのプロンプトを使用）

---

**最終更新**: 2026-03-08
**ステータス**: ✅ 本番稼働中（Spot + Daily）、試験段階（Weekly）
