# USAGE.md - 統合バックテストシステム使用ガイド

統合バックテストシステム（algo4_counter_trade）の詳細な使用方法を説明します。

## 目次

1. [環境セットアップ](#環境セットアップ)
2. [基本的な使用方法](#基本的な使用方法)
3. [設定ファイルの詳細](#設定ファイルの詳細)
4. [データ準備](#データ準備)
5. [バックテスト実行](#バックテスト実行)
6. [結果の解釈](#結果の解釈)
7. [パラメータ調整](#パラメータ調整)
8. [高度な使用例](#高度な使用例)

---

## 環境セットアップ

### 1. 前提条件

- Python 3.8以上
- 仮想環境（推奨）
- 必要なパッケージ: pandas, numpy, PyYAML, matplotlib

### 2. 仮想環境の作成とアクティベート

```powershell
# プロジェクトルートで仮想環境作成
python -m venv .venv

# アクティベート (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 依存パッケージのインストール
pip install -r requirements.txt
```

### 3. ディレクトリ構造の確認

```powershell
cd src/algo4_counter_trade
tree /F
```

必須ディレクトリ:
- `config/`: 設定ファイル
- `input/chart_data/`: チャートデータ（銘柄別）
- `input/market_data/`: 板情報データ（日付別）
- `output/`: 結果出力先（自動作成）

---

## 基本的な使用方法

### 最小限の実行手順

```powershell
# 1. ディレクトリ移動
cd src/algo4_counter_trade

# 2. 設定確認（オプション）
cat config/backtest_config.yaml

# 3. バックテスト実行
python main.py

# 4. 結果確認
cd output/latest
cat summary.json
```

### 実行時の出力例

```
========================================
統合バックテストシステム
========================================
[INFO] 設定ファイル読み込み完了
[INFO] 営業日リスト取得: 2026-01-19 ~ 2026-01-23 (5日間)

[2026-01-19]
  Phase 1: データ読み込み完了 (チャート: 7銘柄, 板情報: 98銘柄)
  Phase 2: レベル生成完了 (140個)
  Phase 3: LOB特徴量計算完了
  Phase 4: バックテスト完了 (5件のトレード)
  Phase 5: 結果保存完了

...

========================================
バックテスト完了
出力ディレクトリ: output/20260124_184915
総トレード数: 5
勝率: 60.0%
総PnL: +15.0 tick
========================================
```

---

## 設定ファイルの詳細

### 1. backtest_config.yaml

バックテスト全体の設定を定義します。

```yaml
# モード設定
mode: backtest  # 'backtest' または 'live' (将来対応)

# バックテスト期間
backtest:
  start_date: "2026-01-19"  # 開始日 (YYYY-MM-DD)
  end_date: "2026-01-23"    # 終了日 (YYYY-MM-DD)

# データパス
data:
  chart_data_dir: "input/chart_data"      # チャートデータディレクトリ
  market_data_dir: "input/market_data"    # 板情報ディレクトリ
  output_base_dir: "output"               # 出力ベースディレクトリ

# データ読み込み設定
data_loading:
  chart_lookback_days: 5                  # チャートデータの遡及日数
  validate_no_future_data: true           # データリーク検証の有効化

# 戦略パラメータ
strategy:
  default_params:                         # デフォルトパラメータ
    k_tick: 3.0                          # エントリー距離（tick）
    x_tick: 15.0                         # ストップロス（tick）
    y_tick: 7.0                          # 利確目標（tick）
    max_hold_bars: 90                    # 最大保有期間（バー数）

# ログ設定
logging:
  level: "INFO"                           # ログレベル (DEBUG, INFO, WARNING, ERROR)
  file: "backtest.log"                    # ログファイル名
  console: true                           # コンソール出力有効化
```

#### 設定項目の説明

- **mode**: 実行モード（現在はbacktestのみサポート）
- **start_date / end_date**: バックテスト期間（営業日のみ自動抽出）
- **chart_lookback_days**: レベル生成に使用する過去チャートデータの日数
- **validate_no_future_data**: データリーク防止チェックの有効化（必須）
- **default_params**: 全銘柄に適用されるデフォルトパラメータ

### 2. level_config.yaml

S/Rレベル生成の設定を定義します。

```yaml
# レベルタイプごとのON/OFF設定
level_types:
  # Pivot高値・安値
  pivot_sr:
    enable: true                          # 有効化フラグ
    lookback_days: 5                      # 遡及日数
    min_bars_between: 3                   # 最小間隔（バー数）
  
  # 値固めゾーン
  consolidation:
    enable: true
    lookback_days: 5
    price_range_pct: 0.5                  # 価格幅閾値（%）
    min_bars: 10                          # 最小バー数
  
  # キリ番
  psychological:
    enable: true
    round_to: 100                         # 丸め単位（例: 100円刻み）
  
  # 5日移動平均
  ma5:
    enable: true
    period: 5                             # 期間
  
  # 25日移動平均
  ma25:
    enable: true
    period: 25                            # 期間

# レベル強度の設定
strength:
  pivot_sr: 1.0                           # Pivot S/Rの強度
  consolidation: 0.8                      # 値固めゾーンの強度
  psychological: 0.6                      # キリ番の強度
  ma5: 0.5                                # 5MA強度
  ma25: 0.7                               # 25MA強度
```

#### レベルタイプの説明

1. **pivot_sr**: 過去の高値・安値から抵抗・支持レベルを生成
2. **consolidation**: 価格が一定範囲内で推移したゾーンを検出
3. **psychological**: キリの良い価格（100円、1000円刻みなど）
4. **ma5 / ma25**: 短期・長期移動平均線

### 3. trade_params.py

銘柄別のパラメータと除外ルールを定義します。

```python
# デフォルトパラメータ
DEFAULT_PARAMS = {
    'k_tick': 3.0,
    'x_tick': 15.0,
    'y_tick': 7.0,
    'max_hold_bars': 90
}

def get_params(symbol: str) -> dict:
    """
    銘柄別パラメータを返す
    
    Args:
        symbol: 銘柄コード（例: "215A", "6758"）
    
    Returns:
        パラメータ辞書
    """
    # 銘柄別カスタマイズ
    if symbol == "215A":
        return {
            'k_tick': 3.0,
            'x_tick': 15.0,
            'y_tick': 7.0,
            'max_hold_bars': 90
        }
    elif symbol == "6758":  # ソニー
        return {
            'k_tick': 5.0,     # より大きなエントリー距離
            'x_tick': 20.0,    # より大きなストップロス
            'y_tick': 10.0,    # より大きな利確目標
            'max_hold_bars': 120
        }
    
    # デフォルトを返す
    return DEFAULT_PARAMS.copy()

def is_excluded(symbol: str) -> bool:
    """
    除外銘柄かどうか判定
    
    Args:
        symbol: 銘柄コード
    
    Returns:
        除外する場合True
    """
    # 除外銘柄リスト
    excluded_symbols = [
        '9999',  # テスト銘柄
        '1234',  # 流動性低
    ]
    
    return symbol in excluded_symbols
```

---

## データ準備

### 1. チャートデータ

#### ディレクトリ構造

```
input/chart_data/
├── 3M_3000_20260119/           # 3分足、3000本、カットオフ日
│   ├── stock_chart_3M_215A_20251208_20260119.csv
│   ├── stock_chart_3M_6758_20251208_20260119.csv
│   └── ...
└── D_3000_20260119/            # 日足、3000本、カットオフ日
    ├── stock_chart_D_215A_20131007_20260119.csv
    ├── stock_chart_D_6758_20131007_20260119.csv
    └── ...
```

#### CSVフォーマット

```csv
timestamp,open,high,low,close,volume
2026-01-19 09:00:00,1000.0,1010.0,995.0,1005.0,100000
2026-01-19 09:03:00,1005.0,1012.0,1003.0,1008.0,120000
...
```

必須カラム:
- `timestamp`: タイムスタンプ (YYYY-MM-DD HH:MM:SS)
- `open`, `high`, `low`, `close`: OHLC価格
- `volume`: 出来高

### 2. 板情報データ

#### ディレクトリ構造

```
input/market_data/
├── 20260119/
│   └── rss_market_data.csv     # 当日の全銘柄板情報
├── 20260120/
│   └── rss_market_data.csv
└── ...
```

#### CSVフォーマット

```csv
timestamp,symbol,bid1_price,bid1_volume,ask1_price,ask1_volume,bid2_price,bid2_volume,ask2_price,ask2_volume,...
2026-01-19 09:00:00.123,215A,1000.0,100,1001.0,150,999.0,200,1002.0,120,...
2026-01-19 09:00:00.456,6758,5000.0,50,5001.0,80,4999.0,100,5002.0,60,...
...
```

必須カラム:
- `timestamp`: ミリ秒精度タイムスタンプ
- `symbol`: 銘柄コード
- `bid1_price` ~ `bid5_price`: 買い気配値（5本）
- `bid1_volume` ~ `bid5_volume`: 買い気配数量（5本）
- `ask1_price` ~ `ask5_price`: 売り気配値（5本）
- `ask1_volume` ~ `ask5_volume`: 売り気配数量（5本）

---

## バックテスト実行

### 1. 通常実行

```powershell
python main.py
```

### 2. ログレベル変更

```powershell
# config/backtest_config.yaml を編集
logging:
  level: "DEBUG"  # より詳細なログ
```

### 3. 期間変更

```powershell
# config/backtest_config.yaml を編集
backtest:
  start_date: "2025-01-01"
  end_date: "2025-12-31"
```

### 4. レベルタイプの変更

```powershell
# config/level_config.yaml を編集
level_types:
  ma5:
    enable: false  # 5日移動平均を無効化
  ma25:
    enable: false  # 25日移動平均を無効化
```

### 5. 統合テスト実行

```powershell
python test_integration.py
```

---

## 結果の解釈

### 1. summary.json

```json
{
  "total_trades": 5,
  "win_rate": 0.6,
  "total_pnl": 15.0,
  "avg_pnl": 3.0,
  "max_win": 10.0,
  "max_loss": -5.0,
  "profit_factor": 2.5,
  "avg_hold_time_minutes": 45.2
}
```

#### 指標の意味

- **total_trades**: 総トレード数
- **win_rate**: 勝率（0.0～1.0）
- **total_pnl**: 総PnL（tick単位）
- **avg_pnl**: 平均PnL（tick単位）
- **max_win**: 最大勝ちトレード（tick）
- **max_loss**: 最大負けトレード（tick）
- **profit_factor**: プロフィットファクター（総利益 / 総損失）
- **avg_hold_time_minutes**: 平均保有時間（分）

### 2. trades.csv

```csv
entry_ts,exit_ts,symbol,direction,entry_price,exit_price,pnl_tick,hold_bars,exit_reason,level
2026-01-19 09:30:00,2026-01-19 10:15:00,215A,long,1000.0,1007.0,7.0,15,target,pivot_sr
2026-01-19 10:20:00,2026-01-19 11:05:00,215A,short,1010.0,1005.0,5.0,15,target,ma5
...
```

#### カラムの意味

- **entry_ts**: エントリータイムスタンプ
- **exit_ts**: 決済タイムスタンプ
- **symbol**: 銘柄コード
- **direction**: 方向（long / short）
- **entry_price**: エントリー価格
- **exit_price**: 決済価格
- **pnl_tick**: PnL（tick単位）
- **hold_bars**: 保有バー数
- **exit_reason**: 決済理由（target / stop / timeout）
- **level**: 使用したレベルタイプ

### 3. グラフの見方

#### pnl_curve.png
累積PnL曲線。右肩上がりが理想。

#### pnl_distribution.png
PnL分布ヒストグラム。正規分布に近いほど安定。

#### symbol_performance.png
銘柄別パフォーマンス。特定銘柄への依存度を確認。

#### exit_reason_breakdown.png
決済理由の内訳。`target`が多いほど良好。

#### hold_time_distribution.png
保有時間分布。極端に長い/短いトレードの有無を確認。

---

## パラメータ調整

### 1. エントリー距離（k_tick）

**効果**: レベルからのエントリー距離

- **小さい値（1～2 tick）**: エントリー機会増加、ダマシ増加
- **大きい値（5～10 tick）**: エントリー機会減少、精度向上

**調整方法**:
```python
# config/trade_params.py
DEFAULT_PARAMS = {
    'k_tick': 5.0,  # 3.0 → 5.0 に変更
    ...
}
```

### 2. ストップロス（x_tick）

**効果**: 最大損失の制限

- **小さい値（5～10 tick）**: 損失抑制、損切り頻度増加
- **大きい値（20～30 tick）**: 余裕あり、損失リスク増加

**調整方法**:
```python
DEFAULT_PARAMS = {
    'x_tick': 20.0,  # 15.0 → 20.0 に変更
    ...
}
```

### 3. 利確目標（y_tick）

**効果**: 利確タイミング

- **小さい値（3～5 tick）**: 利確頻度高、利益小
- **大きい値（10～15 tick）**: 利確頻度低、利益大

**調整方法**:
```python
DEFAULT_PARAMS = {
    'y_tick': 10.0,  # 7.0 → 10.0 に変更
    ...
}
```

### 4. 最大保有期間（max_hold_bars）

**効果**: タイムアウト決済のタイミング

- **短い（30～60バー）**: 資金効率向上、機会損失リスク
- **長い（120～180バー）**: 余裕あり、資金拘束時間増加

**調整方法**:
```python
DEFAULT_PARAMS = {
    'max_hold_bars': 120,  # 90 → 120 に変更
    ...
}
```

---

## 高度な使用例

### 1. 特定銘柄のみバックテスト

```python
# config/trade_params.py を編集
def is_excluded(symbol: str) -> bool:
    # 215A以外を除外
    if symbol != "215A":
        return True
    return False
```

### 2. 期間別バックテスト

```bash
# 2025年Q1
# config/backtest_config.yaml
backtest:
  start_date: "2025-01-01"
  end_date: "2025-03-31"

python main.py
mv output/latest output/2025Q1

# 2025年Q2
# start_date, end_date を変更して再実行
```

### 3. レベルタイプの効果検証

```bash
# Pivot S/Rのみ
# config/level_config.yaml で他を無効化
python main.py
mv output/latest output/pivot_only

# Consolidationのみ
# config/level_config.yaml で他を無効化
python main.py
mv output/latest output/consolidation_only

# 結果比較
cat output/pivot_only/summary.json
cat output/consolidation_only/summary.json
```

### 4. パラメータグリッドサーチ

```python
# optimize_params.py (別途作成)
import subprocess
import json
from pathlib import Path

params_grid = {
    'k_tick': [2.0, 3.0, 5.0],
    'x_tick': [10.0, 15.0, 20.0],
    'y_tick': [5.0, 7.0, 10.0]
}

results = []
for k in params_grid['k_tick']:
    for x in params_grid['x_tick']:
        for y in params_grid['y_tick']:
            # trade_params.py を書き換え
            # ...
            
            # バックテスト実行
            subprocess.run(['python', 'main.py'])
            
            # 結果読み込み
            with open('output/latest/summary.json') as f:
                summary = json.load(f)
            
            results.append({
                'k_tick': k,
                'x_tick': x,
                'y_tick': y,
                'win_rate': summary['win_rate'],
                'total_pnl': summary['total_pnl']
            })

# 最適パラメータを出力
best = max(results, key=lambda r: r['total_pnl'])
print(f"Best params: {best}")
```

---

## トラブルシューティング

詳細なトラブルシューティングは [README.md](README.md#トラブルシューティング) を参照してください。

---

## 関連ドキュメント

- [README.md](README.md): システム概要とクイックスタート
- [DESIGN.md](DESIGN.md): アーキテクチャと設計思想
- [README_legacy.md](README_legacy.md): 旧バージョンのドキュメント
