# 統合バックテストシステム（algo4_counter_trade）

逆張り（カウンタートレード）戦略の統合バックテストシステム。
設定ファイルベースで複数銘柄のバックテストを実行し、データリーク防止機能を備えた再現性の高いシステムです。

## 特徴

- **設定ファイルベース**: YAMLで全パラメータを管理
- **データリーク防止**: カットオフ日以降のデータを厳密に除外
- **レベル生成ON/OFF制御**: 5種類のS/Rレベルを個別に有効化・無効化
- **複数銘柄対応**: 銘柄別パラメータと統一パラメータの両対応
- **再現可能な出力**: タイムスタンプ付きディレクトリに全結果を保存
- **可視化**: 5種類のグラフを自動生成

## システム構成

```
algo4_counter_trade/
├── main.py                     # メインエントリーポイント
├── test_integration.py         # 統合テストスクリプト
├── config/                     # 設定ファイル
│   ├── backtest_config.yaml   # バックテスト設定
│   ├── level_config.yaml      # レベル生成設定
│   └── trade_params.py        # 銘柄別パラメータ
├── core/                       # コアロジック
│   ├── data_loader.py         # データ読み込み
│   ├── level_generator.py     # レベル生成
│   ├── strategy.py            # 戦略ロジック
│   └── backtest_engine.py     # バックテストエンジン
├── processors/                 # データ処理
│   ├── lob_processor.py       # LOB特徴量計算
│   └── ohlc_processor.py      # OHLC生成
├── output_handlers/            # 結果出力
│   ├── result_writer.py       # ファイル出力
│   └── visualizer.py          # グラフ生成
├── utils/                      # ユーティリティ
│   ├── config_validator.py    # 設定検証
│   ├── date_utils.py          # 日付処理
│   ├── output_utils.py        # 出力管理
│   └── validation.py          # データ検証
├── input/                      # 入力データ（空）
└── output/                     # 出力結果
    ├── YYYYMMDD_HHMMSS/       # タイムスタンプ付き結果
    │   ├── trades.csv         # 全トレード記録
    │   ├── summary.json       # 評価指標
    │   ├── levels.jsonl       # レベル情報
    │   ├── symbol_summary.csv # 銘柄別サマリ
    │   ├── exit_reason_summary.csv  # 決済理由別サマリ
    │   ├── pnl_curve.png      # PnL曲線
    │   ├── pnl_distribution.png  # PnL分布
    │   ├── symbol_performance.png  # 銘柄別パフォーマンス
    │   ├── exit_reason_breakdown.png  # 決済理由内訳
    │   ├── hold_time_distribution.png  # 保有時間分布
    │   ├── backtest.log       # 実行ログ
    │   ├── backtest_config_snapshot.yaml  # 設定スナップショット
    │   └── level_config_snapshot.yaml     # 設定スナップショット
    └── latest/                # 最新結果へのリンク/コピー
```

## クイックスタート

### 1. 設定ファイルの確認

#### `config/backtest_config.yaml`
```yaml
mode: backtest
backtest:
  start_date: "2026-01-19"
  end_date: "2026-01-23"
data:
  chart_data_dir: "input/chart_data"
  market_data_dir: "input/market_data"
  output_base_dir: "output"
```

#### `config/level_config.yaml`
```yaml
level_types:
  pivot_sr:
    enable: true  # Pivot高値・安値
  consolidation:
    enable: true  # 値固めゾーン
  psychological:
    enable: true  # キリ番
  ma5:
    enable: true  # 5日移動平均
  ma25:
    enable: true  # 25日移動平均
```

### 2. バックテスト実行

```powershell
# 仮想環境アクティベート
.\.venv\Scripts\Activate.ps1

# 実行
cd src/algo4_counter_trade
python main.py
```

### 3. 結果確認

```powershell
# 最新結果ディレクトリを開く
cd output/latest

# トレード記録を確認
cat trades.csv

# 評価指標を確認
cat summary.json
```

### 4. 統合テスト実行

```powershell
# 統合テストを実行
python test_integration.py
```

## 出力ファイル

### CSV/JSON出力

1. **trades.csv**: 全トレード記録
   - entry_ts, exit_ts, symbol, direction, entry_price, exit_price
   - pnl_tick, hold_bars, exit_reason, level

2. **summary.json**: 評価指標
   - total_trades, win_rate, total_pnl, avg_pnl
   - max_win, max_loss, profit_factor, avg_hold_time_minutes

3. **levels.jsonl**: レベル情報（1行1レベル）
   - symbol, price, type, strength, lookback_days

4. **symbol_summary.csv**: 銘柄別サマリ
   - symbol, trades, total_pnl, avg_pnl, avg_hold_bars, win_rate

5. **exit_reason_summary.csv**: 決済理由別サマリ
   - exit_reason, trades, total_pnl, avg_pnl, avg_hold_bars

### グラフ出力

1. **pnl_curve.png**: 累積PnL曲線
2. **pnl_distribution.png**: PnL分布ヒストグラム
3. **symbol_performance.png**: 銘柄別パフォーマンス棒グラフ
4. **exit_reason_breakdown.png**: 決済理由内訳円グラフ
5. **hold_time_distribution.png**: 保有時間分布ヒストグラム

## バックテストフロー

```
1. 設定ファイル読み込み
   ↓
2. 営業日リスト取得（start_date ～ end_date）
   ↓
3. 各営業日で以下を実行:
   ├── Phase 1: データ読み込み（target_date以前のみ）
   │   ├── チャートデータ（過去5営業日）
   │   └── 板情報（当日のみ）
   │
   ├── Phase 2: S/Rレベル生成
   │   ├── Pivot高値・安値
   │   ├── 値固めゾーン
   │   ├── キリ番
   │   ├── 5日移動平均
   │   └── 25日移動平均
   │
   ├── Phase 3: LOB特徴量計算
   │   ├── スプレッド、ミッド価格
   │   ├── マイクロ価格、バイアス
   │   ├── Order Flow Imbalance
   │   └── Depth Imbalance
   │
   └── Phase 4: バックテスト実行
       ├── エントリーシグナル検出
       ├── 決済シグナル監視
       └── トレード記録
   ↓
4. 全結果を集約
   ↓
5. 結果出力（CSV/JSON/PNG）
```

## データリーク防止

### カットオフ日の厳密な管理

```python
# チャートデータ: target_date以前のみ
chart_data = data_loader.load_chart_data_until(target_date, lookback_days=5)

# 板情報: target_date当日のみ
market_data = data_loader.load_market_data_for_date(target_date)
```

### 検証

DataLoaderが内部で未来データチェックを実施し、混入があればエラーを発生させます：

```python
if validate_no_future_data and (data['timestamp'] > cutoff_date).any():
    raise DataLeakError(f"未来データ検出: {symbol}")
```

## カスタマイズ

### 1. バックテスト期間の変更

`config/backtest_config.yaml`:
```yaml
backtest:
  start_date: "2025-01-01"
  end_date: "2025-12-31"
```

### 2. レベルタイプのON/OFF

`config/level_config.yaml`:
```yaml
level_types:
  pivot_sr:
    enable: true  # 有効
  ma5:
    enable: false  # 無効
```

### 3. 銘柄別パラメータの設定

`config/trade_params.py`:
```python
def get_params(symbol: str) -> dict:
    if symbol == "215A":
        return {
            'k_tick': 3.0,
            'x_tick': 15.0,
            'y_tick': 7.0,
            'max_hold_bars': 90
        }
    return DEFAULT_PARAMS
```

### 4. 除外銘柄の設定

`config/trade_params.py`:
```python
def is_excluded(symbol: str) -> bool:
    excluded_symbols = ['9999', '1234']
    return symbol in excluded_symbols
```

## トラブルシューティング

### データが見つからない

```
FileNotFoundError: チャートデータディレクトリが存在しません
```

→ `config/backtest_config.yaml`でデータパスを確認してください

### レベルが生成されない

```
レベル生成完了: 0個
```

→ チャートデータが不足している可能性があります。`lookback_days`を調整してください

### トレードが発生しない

```
バックテスト完了: 0件のトレード
```

→ 以下を確認:
1. レベルが生成されているか（`levels.jsonl`）
2. LOB特徴量が計算されているか（ログ確認）
3. パラメータ（`k_tick`, `x_tick`, `y_tick`）が適切か

## パフォーマンス

- **処理速度**: 約1営業日/秒（7銘柄、98銘柄板情報）
- **メモリ使用量**: 約500MB（7銘柄×5日チャート + 98銘柄板情報）
- **出力サイズ**: 約300KB（5件トレード + 140レベル + グラフ5枚）

## 既知の制限

1. **チャートデータ依存**: 一部のレベル生成（MA等）はチャートデータが必須
2. **LOBカラム依存**: 板情報の特定カラムが存在しない場合、その銘柄はスキップ
3. **日本語フォント**: グラフの日本語表示には`Yu Gothic`または`MS Gothic`が必要

## 旧バージョンからの移行

旧バージョン（algo4_counter_trade2）からの移行については、[README_legacy.md](README_legacy.md)を参照してください。

主な変更点：
- フェーズ別実行 → 統合実行（main.py）
- 複数スクリプト → 単一エントリーポイント
- ハードコードパラメータ → YAML設定ファイル
- 手動データリーク管理 → 自動データリーク防止

## ライセンス

Proprietary - Internal Use Only

## 更新履歴

### v1.0.0 (2026-01-24)
- 統合バックテストシステム初版リリース
- 設定ファイルベース、データリーク防止、5種類のレベル生成
- 5種類のCSV/JSON出力 + 5種類のグラフ生成
- 統合テストスクリプト追加
