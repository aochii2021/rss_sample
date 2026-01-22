# Copilot / Agent 共通ルール（必読）

本リポジトリでは、すべてのエージェントは以下の方針に必ず従うこと。

---

## Language Policy（最重要）

- 人間向けのすべての出力は **日本語で記述する**
  - 計画
  - 説明
  - レビューコメント
  - 判断理由
  - 指摘事項
- 以下は **原文（英語）を一切変更せず、そのまま使用する**
  - コンパイラ／ランタイム／テストのエラーメッセージ
  - スタックトレース
  - コード上の識別子（関数名・変数名・クラス名・API名）
  - コマンド、オプション名、設定キー

👉 日本語は「説明・要約・意図の明確化」に限定すること。

---

## Code Language Policy

- 識別子名：英語のみ
- Public API 名称：英語のみ
- コメント言語：日本語（※本プロジェクトでは日本語を正式採用）
- README / ADR / 設計資料：日本語

---

## Engineering Principles

- 差分は常に小さく、レビュー可能な単位に分割する
- 動作変更には必ず根拠（仕様・テスト・ログ）を示す
- 「なぜそうしたか」を日本語で説明できない変更は行わない
- 推測・仮定がある場合は必ず明示する

---

## Safety & Quality

- セキュリティ・互換性・保守性を常に優先する
- 不明点がある場合は独断で進めず、前提条件として明記する
- 既存設計・命名・構造を尊重する

---

## Git操作安全ルール（最重要・必須遵守）

### ファイル・ディレクトリ削除前の必須確認

**絶対にこの手順を省略してはならない。データ損失の原因となる。**

1. **Git管理外ファイルの確認**
   ```powershell
   # 削除対象ディレクトリ内のGit管理外ファイルを確認
   git status --ignored <対象ディレクトリ>
   git ls-files --others --exclude-standard <対象ディレクトリ>
   ```
   - `.csv`, `.jsonl`, `.xlsx`, `.log` などのデータファイルは通常Git管理外
   - `input/`, `output/` ディレクトリは特に注意が必要

2. **重要データの識別**
   - 市場データ（板情報、チャートデータ）: `rss_market_data.csv`, `stock_chart_*.csv`
   - バックテスト結果: `trades.csv`, `backtest_summary.json`, `levels.jsonl`
   - LOB特徴量: `lob_features.csv`, `ohlc_*.csv`
   - **これらは再取得が困難または不可能なため、削除前に必ずバックアップまたはGit管理下に置く**

3. **削除前のユーザー確認**
   - Git管理外ファイルが存在する場合、削除前に必ずユーザーに報告し、確認を取る
   - 「〇〇ディレクトリにGit管理外のファイル（rss_market_data.csv等）があります。削除してよろしいですか？」

### ディレクトリ移動・リネーム時の安全手順

1. **Git管理下のリネーム**
   ```powershell
   # 正しい手順
   git mv <元のパス> <新しいパス>
   ```
   - `git mv` を使用すれば履歴が保持される
   - PowerShellの `Rename-Item` や `Move-Item` は使用禁止（Git管理外ファイルが残る）

2. **Git管理外ファイルの移動**
   ```powershell
   # 移動前に確認
   Get-ChildItem <元のディレクトリ> -Recurse -File | Where-Object { !(git ls-files $_.FullName) }
   
   # 手動で移動
   Copy-Item -Path <元のパス> -Destination <新しいパス> -Recurse -Force
   ```

3. **リネーム後の検証**
   ```powershell
   # 重要ファイルが移動されたか確認
   Test-Path <新しいパス>/input/market_order_book/*/rss_market_data.csv
   ```

### 禁止事項

- ❌ `Remove-Item -Recurse -Force` の無確認実行
- ❌ Git管理外ファイルの存在確認なしのディレクトリ削除
- ❌ `input/`, `output/` ディレクトリの無確認削除
- ❌ PowerShellコマンドによるGit管理下ディレクトリのリネーム（必ず `git mv` を使用）

### データ損失発生時の対応

1. 直ちにユーザーに報告
2. 復旧可能性の調査（ゴミ箱、`git reflog`、バックアップ）
3. 再取得方法の提示
4. 再発防止策の実施
