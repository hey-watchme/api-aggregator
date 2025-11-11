# 🚨 文字化け問題 - 緊急調査引き継ぎ

**作成日**: 2025-11-11
**優先度**: 🔴 最高
**状況**: aggregatorプロジェクト全体でUTF-8エンコーディングエラーが発生

---

## 📋 現在の状況サマリー

### 発生している問題
- **aggregatorプロジェクトの複数のPythonファイルが文字化けしている**
- 本番環境でコンテナが起動できない（SyntaxError: unicode error）
- 過去100日以上使用して初めての文字化け現象

### 影響範囲
- ✅ `main.py` - **修正済み**（UTF-8で書き直し済み）
- ❌ `config.py` - 文字化けあり（バイナリデータ混入）
- ❌ `endpoints/spot_aggregator.py` - 文字化けあり
- ❌ `utils/supabase_client.py` - 文字化けあり
- ❌ `services/prompt_generator.py` - 文字化けあり
- ❌ `services/subject_fetcher.py` - 文字化けあり
- ❌ `services/context_builder.py` - 文字化けあり
- ❌ `services/data_fetcher.py` - 文字化けあり

---

## 🔍 判明している事実

### 1. 文字化けの証拠

**ファイルエンコーディング確認結果**:
```bash
$ find . -name "*.py" -type f -exec file {} \;
./config.py: data                           # ❌ 異常（本来はUTF-8 text）
./endpoints/spot_aggregator.py: data        # ❌ 異常
./main.py: Python script, UTF-8 text        # ✅ 正常（修正済み）
./services/prompt_generator.py: data        # ❌ 異常
# 他のファイルも全て data = バイナリ扱い
```

### 2. バイナリ解析結果（config.py）

```
00000020  3d 3d 3d 3d 3d 3d 3d 3d  3d 3d 3d 3d 3d 0a b0 83  |=============...|
00000030  09 70 68 2d 9a 92 a1 06  0a 22 22 22 0a 0a 69 6d  |.ph-....."""..im|
                                  ^^^^^^^^^^  ← 不正なバイト列

00000060  64 6f 74 65 6e 76 0a 0a  23 20 2e 65 6e 76 d5 a1  |dotenv..# .env..|
00000070  a4 eb 92 ad 7f bc 7f 0a  6c 6f 61 64 5f 64 6f 74  |........load_dot|
                            ^^^^^^^^^^^^^^^^^^  ← 不正なバイト列

00000090  65 2d 9a 0a 53 55 50 41  42 41 53 45 5f 55 52 4c  |e-..SUPABASE_URL|
      ^^^^^^  ← 不正なバイト
```

**パターン**: 日本語コメント部分に不正なバイト列が混入

### 3. Git履歴の確認結果

```bash
$ git log --oneline
c600e5c fix: repair UTF-8 encoding errors in main.py
651629c fix: add missing deployment steps to CI/CD workflow
71cc73c test: trigger CI/CD for deployment
026a548 feat: Aggregator API implementation  # ← 初回コミット
```

**重要**: 初回コミット（026a548）時点で既に文字化けしていた
```bash
$ git show 026a548:config.py | hexdump -C
# 結果: 初回から同じ不正バイト列が存在
```

### 4. エラーメッセージ（本番環境）

```
File "/app/main.py", line 7
    """
       ^
SyntaxError: (unicode error) 'utf-8' codec can't decode byte 0xd7 in position 18: invalid continuation byte
```

---

## 🎯 推定される原因

### 仮説1: Writeツールのエンコーディング問題（最有力）
- **可能性**: Claudeの`Write`ツールが日本語コメントを正しくUTF-8でエンコードしていない
- **根拠**:
  - 過去100日以上問題なかったのに、今回初めて発生
  - 複数ファイルで同じパターンの文字化け
  - 初回コミット時点で既に壊れている

### 仮説2: ローカル環境の問題
- **可能性**: MacのファイルシステムまたはGitの設定問題
- **根拠**:
  - 可能性は低い（他のプロジェクトでは発生していない）

### 仮説3: コピー元のコードに問題
- **可能性**: 既存の`vibe-aggregator`から流用したコードに問題
- **根拠**:
  - 確認が必要

---

## 📋 次のセッションでやるべきこと

### ✅ 優先度1: 全ファイルの修正（最優先）

#### Step 1: 壊れたファイルのリストアップ
```bash
cd /Users/kaya.matsumoto/projects/watchme/api/aggregator
find . -name "*.py" -type f -exec sh -c 'file "$1" | grep -q "data" && echo "$1"' _ {} \;
```

#### Step 2: 各ファイルを1つずつ読み取り
```bash
# 例: config.py
cat config.py
# → 文字化けしている部分を特定
```

#### Step 3: 正しいUTF-8で書き直し
- **必須**: Readツールで既存内容を確認してから、Writeツールで正しく書き直す
- **注意**: 日本語コメントは避けるか、英語に変更することを推奨

#### Step 4: エンコーディング確認
```bash
file config.py
# 期待結果: Python script text executable, UTF-8 text
```

### ✅ 優先度2: 原因の特定

#### 調査A: 流用元のファイル確認
```bash
cd /Users/kaya.matsumoto/projects/watchme/api/vibe-analysis/aggregator
find . -name "*.py" -exec file {} \; | grep data
# 流用元も壊れているか確認
```

#### 調査B: 他のAPIプロジェクトの確認
```bash
# 同じ時期に作成された他のAPIで文字化けがないか確認
cd /Users/kaya.matsumoto/projects/watchme/api/
for dir in */; do
  echo "=== $dir ==="
  find "$dir" -name "*.py" -exec file {} \; | grep data
done
```

#### 調査C: GitHubリポジトリの直接確認
- ブラウザでGitHub上のファイルを確認
- GitHub上でも文字化けしているか？
  - Yes → ローカルで作成時に既に壊れていた
  - No → git push時に壊れた

### ✅ 優先度3: デプロイと動作確認

#### Step 5: 修正後の再デプロイ
```bash
git add .
git commit -m "fix: repair all UTF-8 encoding errors"
git push origin main
```

#### Step 6: 本番環境での起動確認
```bash
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82
docker ps | grep aggregator-api
docker logs aggregator-api --tail 50
curl http://localhost:8050/health
```

---

## 🔧 修正テンプレート

### 対象ファイルリスト（優先順）

1. **config.py** - 環境変数管理
2. **utils/supabase_client.py** - Supabase接続
3. **services/data_fetcher.py** - データ取得
4. **services/context_builder.py** - コンテキスト生成
5. **services/subject_fetcher.py** - 観測対象者取得
6. **services/prompt_generator.py** - プロンプト生成
7. **endpoints/spot_aggregator.py** - APIエンドポイント

### 修正手順（各ファイル共通）

```bash
# 1. 現在の内容を確認
cat <file>

# 2. 不正なバイト部分を特定
hexdump -C <file> | grep -B2 -A2 "[\x80-\xff]"

# 3. Readツールで読み取り（Claude Code）
# 4. Writeツールで正しく書き直し（Claude Code）

# 5. 確認
file <file>  # UTF-8 text になるか確認
python3 -m py_compile <file>  # 構文エラーがないか確認
```

---

## 📊 修正の進捗管理

```markdown
- [x] main.py - 修正完了
- [ ] config.py
- [ ] utils/supabase_client.py
- [ ] services/data_fetcher.py
- [ ] services/context_builder.py
- [ ] services/subject_fetcher.py
- [ ] services/prompt_generator.py
- [ ] endpoints/spot_aggregator.py
```

---

## ⚠️ 重要な注意事項

### 1. 日本語コメントの扱い
- **推奨**: 日本語コメントは英語に変更する
- **理由**: 今回のような文字化け問題を避けるため

### 2. Writeツールの使用
- **必須**: ファイルを書き直す際は、必ず正しいUTF-8文字列であることを確認
- **方法**: エディタで開いて目視確認、または `file` コマンドで確認

### 3. Git管理
- 修正のたびにコミット（履歴として残す）
- コミットメッセージに修正内容を明記

---

## 🔗 関連ファイル

- **このドキュメント**: `/Users/kaya.matsumoto/projects/watchme/api/aggregator/ENCODING_ISSUE_INVESTIGATION.md`
- **プロジェクトディレクトリ**: `/Users/kaya.matsumoto/projects/watchme/api/aggregator/`
- **GitHubリポジトリ**: `https://github.com/hey-watchme/api-aggregator`
- **本番環境**: `ubuntu@3.24.16.82:/home/ubuntu/aggregator/`

---

## 📝 調査ログ

### 2025-11-11 Session 1
- main.pyの文字化けを発見、修正完了
- 他のファイルも文字化けしていることが判明
- 初回コミット時点で既に文字化けしていたことを確認
- 原因は特定できず、次のセッションに引き継ぎ

---

**次のアクション**: 上記「優先度1: 全ファイルの修正」から開始してください
