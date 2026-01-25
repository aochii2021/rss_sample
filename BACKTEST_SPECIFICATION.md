# バックテストシステム仕様書

## 概要

このバックテストシステムは、order book（板情報）とLevel-of-Book（LOB）特徴量を活用した**カウンタートレード戦略**を検証するものです。複数銘柄の短期トレード機会を自動検出し、エントリー・エグジット、リスク管理を含めた総合的な取引シミュレーションを実施します。

**最新実行日**: 2026-01-25  
**実行期間**: 2026-01-19 ～ 2026-01-23（5営業日）  
**総トレード数**: 46件  
**総損益**: +79.0 tick  
**勝率**: 52.2%

---

## システムアーキテクチャ

```
src/algo4_counter_trade/
├── core/
│   ├── data_loader.py          # チャートデータ・板情報読み込み
│   ├── level_generator.py      # サポート/レジスタンスレベル生成
│   ├── backtest_engine.py      # トレード実行・決済ロジック
│   └── strategy.py             # エントリー/エグジット判定
├── processors/
│   └── lob_processor.py        # LOB特徴量計算
├── output_handlers/
│   ├── visualizer.py           # チャート可視化・トレードチャート生成
│   └── result_writer.py        # 結果出力（CSV/JSON）
├── config/
│   └── backtest_config.yaml    # バックテスト設定
└── main.py                     # メイン実行スクリプト
```

---

## 実行フロー

### Phase 1: データ読み込み
- **チャートデータ**
  - 3分足（3M）: 過去5営業日分（テクニカル分析用）
  - 日足（D）: 過去全期間（トレンド判定用）
  - 読み込み: `src/get_rss_chart_data/output/` から自動取得

- **板情報データ（Order Book）**
  - 当日の板情報スナップショット
  - 読み込み: `src/get_rss_market_order_book/output/YYYYMMDD/` から自動取得
  - 利用: LOB特徴量計算用

### Phase 2: レベル生成

以下の5種類のレベルを自動生成:

| レベル種別 | 説明 | 計算方法 |
|-----------|------|--------|
| **pivot_sr** | ピボット支持抵抗 | 前日のOHCの組み合わせ（標準ピボット） |
| **consolidation** | もみ合い | 過去20本の高値・安値範囲 |
| **psychological** | 心理的抵抗 | 100、500、1000等の切り良い価格 |
| **ma5** | 5本平均 | 3分足の単純移動平均 |
| **ma25** | 25本平均 | 3分足の単純移動平均 |

**レベル数**: 銘柄あたり40個（平均）

### Phase 3: LOB特徴量計算

板情報から以下の特徴量を計算:

- **Bid-Ask Spread**: 買値と売値の差幅
- **Imbalance**: 買い・売りの板の枚数不均衡
- **Momentum**: 短期の価格変動率
- **その他**: VPOC（出来高加重ポイント）等

### Phase 4: バックテスト実行（コアロジック）

#### エントリー判定
```
条件: level を突破 + LOB特徴量が売買シグナル

買い: 
  - レベル（サポート）を下から上に突破
  - 買い圧が高い（Imbalance > 閾値）

売り:
  - レベル（レジスタンス）を上から下に突破
  - 売り圧が高い（Imbalance < 閾値）
```

#### ポジション管理
```
戦略パラメータ（デフォルト）:
  k = 5.0                    # レベル突破の幅（tick）
  x = 10.0                   # 利確目標（tick）
  y = 5.0                    # 損切ルール（tick）
  max_hold = 60              # 最大保有本数（3分足）= 180分 ≈ 3時間
```

#### エグジット（決済）ロジック
| 決済理由 | 内容 |
|--------|------|
| **profit_target** | 利確：目標利益 x tick に達した |
| **stop_loss** | 損切：損失 y tick に達した |
| **hold_time_limit** | 時間切れ：max_hold 本保有した |
| **close_signal** | 反転シグナル：反対方向の強いシグナル検出 |

---

## 出力結果

### 1. トレードデータ

**ファイル**: `output/trades.csv`

```csv
trade_id,symbol,direction,entry_time,exit_time,entry_price,exit_price,
exit_reason,pnl_tick,pnl_yen,level,holding_bars
0,215A,buy,2026-01-20 10:32:00,2026-01-20 10:35:00,2101.5,2104.0,
profit_target,25,2500,2100.0,3
```

**列説明**:
- `trade_id`: トレード通し番号
- `symbol`: 銘柄コード
- `direction`: 売買方向（buy/sell）
- `entry_time`, `exit_time`: エントリー・エグジット時刻（UTC）
- `entry_price`, `exit_price`: エントリー・エグジット価格
- `exit_reason`: 決済理由（上表参照）
- `pnl_tick`: 損益（ティック）
- `pnl_yen`: 損益（円）= pnl_tick × 100
- `level`: 使用したレベル価格
- `holding_bars`: 保有本数

### 2. パフォーマンス集計

**ファイル**: `output/performance_by_symbol_date.csv`

```csv
symbol,date,trades,wins,win_rate,total_pnl,avg_pnl,max_pnl,min_pnl,avg_hold_bars
215A,2026-01-20,4,2,50.0,15.0,3.75,5.0,-2.0,3.0
3350,2026-01-21,12,7,58.3,52.0,4.33,8.0,-3.0,4.1
```

**列説明**:
- `symbol`: 銘柄コード
- `date`: 取引日
- `trades`: トレード数
- `wins`: 勝利数
- `win_rate`: 勝率（%）
- `total_pnl`: 合計損益（tick）
- `avg_pnl`: 平均損益（tick/トレード）
- `max_pnl`: 最大利益（tick）
- `min_pnl`: 最大損失（tick）
- `avg_hold_bars`: 平均保有時間（3分足本数）

### 3. サマリー集計

**ファイル**: `output/summary.json`

```json
{
  "total_trades": 46,
  "total_pnl": 79.0,
  "win_rate": 52.2,
  "symbols": ["215A", "3350", "5016", "6526", "9501", "9509"],
  "date_range": {
    "start": "2026-01-20",
    "end": "2026-01-23"
  }
}
```

### 4. レベル情報

**ファイル**: `output/levels.jsonl`（行区切りJSON）

```json
{"symbol": "3350", "timestamp": "2026-01-20T09:00:00", "level_price": 2100.5, "kind": "pivot_sr", "strength": 3}
{"symbol": "3350", "timestamp": "2026-01-20T09:00:00", "level_price": 2099.0, "kind": "consolidation", "strength": 2}
```

### 5. トレードチャート

**ファイル**: `output/trade_chart_{SYMBOL}.png`

**内容**:
- **上段**: OHLC（ローソク足） + 出来高プロファイル
- **レベルラインと注釈**:
  - 赤破線: サポート/レジスタンスレベル
  - ラベル（日本語）: レベル種別、日付、足種（日足/分足）、近くのレベル種別
  - 例: `ピボット安値\n(2026-01-20\n日足)\n2100.5\n心理的抵抗`
- **中段**: トレード位置マーカー
  - 💚 緑: 買いエントリー
  - 💔 赤: 売りエントリー
- **下段**: 保有バー数推移

---

## 実行方法

### 前提条件

1. **環境セットアップ**
   ```bash
   cd mksp2_sample
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **データの準備**
   ```
   チャートデータ: src/get_rss_chart_data/output/
   板情報データ: src/get_rss_market_order_book/output/
   ```

### 実行コマンド

#### 基本実行
```bash
cd mksp2_sample
python src/algo4_counter_trade/main.py
```

#### 特定期間でバックテスト
[backtest_config.yaml を編集]
```yaml
backtest:
  start_date: "2026-01-20"
  end_date: "2026-01-23"
```

#### ログ確認
```bash
# 実行中のプログレス表示
# 出力例:
# 2026-01-25 02:31:28 - __main__ - INFO - ✓ バックテスト完了: 46件のトレード
# 2026-01-25 02:31:28 - __main__ - INFO -   - 合計損益: +79.0 tick
# 2026-01-25 02:31:28 - __main__ - INFO -   - 勝率: 52.2%
```

### 出力先

```
runs/
├── 20260125_023127/              # 実行タイムスタンプ
│   ├── input/
│   │   ├── backtest_config.yaml
│   │   ├── level_config.yaml
│   │   └── target_symbols.csv
│   └── output/
│       ├── trades.csv
│       ├── summary.json
│       ├── levels.jsonl
│       ├── symbol_summary.csv
│       ├── exit_reason_summary.csv
│       ├── performance_by_symbol_date.csv
│       ├── pnl_curve.png
│       ├── pnl_distribution.png
│       ├── symbol_performance.png
│       ├── exit_reason_breakdown.png
│       ├── hold_time_distribution.png
│       └── trade_chart_*.png          # 銘柄別トレードチャート
└── latest/                       # 最新実行へのシンボリックリンク
```

---

## パラメータ調整

### backtest_config.yaml

```yaml
backtest:
  start_date: "2026-01-20"        # テスト開始日
  end_date: "2026-01-23"          # テスト終了日
  
strategy:
  k: 5.0                          # レベル突破幅（tick）
  x: 10.0                         # 利確目標（tick）
  y: 5.0                          # 損切ルール（tick）
  max_hold: 60                    # 最大保有本数
  
level_generation:
  enabled_types:
    - pivot_sr                    # ピボット支持抵抗
    - consolidation               # もみ合い
    - psychological               # 心理的抵抗
    - ma5                         # 5本平均
    - ma25                        # 25本平均
```

### level_config.yaml

各レベルの生成パラメータ（詳細は省略）

---

## データフロー図

```
チャートデータ (3分足5日, 日足全期間)
        ↓
   ├─→ テクニカル分析
   └─→ ピボット計算
        ↓
    板情報データ (当日)
        ↓
   LOB特徴量計算
   (Spread, Imbalance, etc.)
        ↓
  ┌─────────────────────┐
  │  レベル生成         │
  │  (5種類 × 40個)     │
  └─────────────────────┘
        ↓
  ┌─────────────────────┐
  │  バックテスト       │
  │  - エントリー判定   │
  │  - ポジション管理   │
  │  - 決済ロジック     │
  └─────────────────────┘
        ↓
  ┌─────────────────────┐
  │  結果出力           │
  │  - トレードデータ   │
  │  - パフォーマンス   │
  │  - 可視化チャート   │
  └─────────────────────┘
```

---

## トラブルシューティング

### Q: "レベルなし、スキップ" が出力される

**原因**: 当該日付のレベル生成に失敗  
**対策**:
- チャートデータが存在するか確認
- level_config.yaml のパラメータを確認
- ログで詳細エラーを確認

### Q: トレードが一件も発生しない

**原因**: LOB特徴量の計算に失敗  
**対策**:
- 板情報ファイルが存在するか確認
- 銘柄がターゲットシンボル（target_symbols.csv）に含まれているか確認
- 戦略パラメータを調整（k, x, y の値を変更）

### Q: チャート生成が失敗する

**原因**: データ型の不一致（Timestamp型が期待値と異なる）  
**対策**:
- visualizer.py で str(timestamp) 変換を確認
- OHLC データの日付範囲を確認

---

## 最新実行結果（2026-01-25実行）

```
実行期間: 2026-01-20 ～ 2026-01-23
総トレード: 46件
  - 2026-01-20: 4件 (+15.0 tick, 勝率 50.0%)
  - 2026-01-21: 28件 (+58.7 tick, 勝率 53.6%)
  - 2026-01-23: 14件 (+5.3 tick, 勝率 50.0%)

対象銘柄: 6銘柄（215A, 3350, 5016, 6526, 9501, 9509）
レベル総数: 1,071個

出力ファイル:
  ✓ trades.csv
  ✓ summary.json
  ✓ levels.jsonl
  ✓ performance_by_symbol_date.csv
  ✓ symbol_summary.csv
  ✓ exit_reason_summary.csv
  ✓ トレードチャート × 6銘柄
  ✓ パフォーマンス可視化 × 5種類
```

---

## 今後の拡張

- [ ] リアルタイムトレード対応
- [ ] 複数戦略の並行実行
- [ ] より高度なリスク管理（Kelly Criterion等）
- [ ] 機械学習ベースのパラメータ最適化
- [ ] API連携（ブローカー自動注文）
