# 逆張りアルゴ（algo4_counter_trade2）

MarketSpeed II（MS2）のRSS生CSVから、LOB特徴量とサポート/レジスタンスレベルを活用した逆張り（ミーンリバージョン）戦略のバックテストシステムです。

## 📁 ファイル構成

```
algo4_counter_trade2/
├── main.py                      # 統合実行スクリプト
├── config.py                    # 設定管理（パラメータ/除外銘柄）
├── validation.py                # データ検証機能
├── lob_features.py              # LOB特徴量計算
├── ohlc_from_rss.py            # MS2データから分足OHLC生成
├── sr_levels.py                # サポート/レジスタンス抽出
├── viz_quicklook.py            # 可視化
├── backtest_mean_reversion.py  # 逆張りバックテスト
├── optimize_params.py          # パラメータ最適化（グリッドサーチ）
├── analyze_trade_timing.py     # トレードタイミング分析
├── Algo_Dev_Spec.md            # 詳細仕様書
├── README.md                   # 本ファイル
├── input/
│   └── rss_market_data.csv    # MS2 RSSデータ（入力）
└── output/
    ├── lob_features.csv       # LOB特徴量
    ├── ohlc_1min.csv          # 分足OHLC
    ├── levels_by_symbol.jsonl # サポレジレベル（銘柄別）
    ├── trades.csv             # トレード履歴
    ├── backtest_summary.json  # バックテスト結果
    ├── optimized_params_all.json  # 最適化パラメータ（全銘柄）
    └── figs/
        ├── lob_timeline_*.png # LOB時系列（銘柄別）
        └── ohlc_levels_*.png  # OHLC+レベル線+トレード点（銘柄別）
```

## 🚀 使い方

### 1. 全フェーズ一括実行

```bash
python main.py --phase all
```

### 2. フェーズ別実行

```bash
# Phase 1: LOB特徴量 + OHLC生成
python main.py --phase 1

# Phase 2: サポート/レジスタンス抽出
python main.py --phase 2

# Phase 3: 可視化
python main.py --phase 3

# Phase 4: バックテスト
python main.py --phase 4
```

### 3. 個別スクリプト実行

```bash
# LOB特徴量
python lob_features.py --rss input/rss_market_data.csv --out output/lob_features.csv --roll-n 20 --k-depth 5

# OHLC生成
python ohlc_from_rss.py --rss input/rss_market_data.csv --out output/ohlc_1min.csv --freq 1min

# サポレジ抽出
python sr_levels.py --min1 output/ohlc_1min.csv --out output/levels.jsonl --bin-size 1.0 --lookback-bars 180 --pivot-left 3 --pivot-right 3

# 可視化（LOB）
python viz_quicklook.py lob --lob input/rss_market_data.csv --out output/figs/lob_timeline.png

# 可視化（OHLC+レベル）
python viz_quicklook.py ohlc --ohlc output/ohlc_1min.csv --levels output/levels.jsonl --out output/figs/ohlc_levels.png

# バックテスト
python backtest_mean_reversion.py --lob-features output/lob_features.csv --levels output/levels.jsonl --out-trades output/trades.csv --out-summary output/backtest_summary.json --k-tick 5.0 --x-tick 10.0 --y-tick 5.0
```

## 📊 LOB特徴量

### 計算される特徴量

- **spread**: 最良売気配値1 - 最良買気配値1
- **mid**: (最良売気配値1 + 最良買気配値1) / 2
- **qi_l1**: Quantity Imbalance = (Bid1_qty - Ask1_qty) / (Bid1_qty + Ask1_qty)
- **microprice**: (Ask1*Bid1_qty + Bid1*Ask1_qty) / (Bid1_qty + Ask1_qty)
- **micro_bias**: microprice - mid
- **ofi_N**: Order Flow Imbalance（N期間ローリング合計）
- **depth_imb_k**: 累積厚み差（L1〜Lkの集計）

### パラメータ

- `--roll-n`: OFIのローリング窓（デフォルト: 20）
- `--k-depth`: 板厚み集計段数（デフォルト: 5）

## 🎯 サポート/レジスタンスレベル

### 抽出されるレベル種別

1. **recent_high / recent_low**: 直近N本の高値・安値
2. **vpoc / hvn**: 価格帯別出来高（Volume Point of Control / High Volume Node）
3. **swing_resistance / swing_support**: スイング高値・安値（フラクタル）
4. **prev_high / prev_low / prev_close**: 前日高値・安値・終値

### 強度スコア（0-1）

各レベルには強度スコア（strength）が付与され、バックテストでフィルタリングに使用されます。

### パラメータ

- `--bin-size`: 価格ビン幅（デフォルト: 1.0）
- `--lookback-bars`: 直近高安の範囲（デフォルト: 180）
- `--pivot-left / --pivot-right`: スイング検出窓（デフォルト: 3）

## 📈 逆張り戦略

### 基本ロジック

1. **レベル選定**: 強度閾値（strength_threshold）を超えるレベルを採用
2. **反応帯判定**: レベル ± k_tick の範囲に価格が入る
3. **シグナル**: 以下のいずれかが反転方向を示す
   - micro_bias の符号
   - OFI_N の符号
   - QI の符号
   - depth_imb の符号
4. **エントリー**: 反応帯内で反転シグナルが出たら売買
5. **エグジット**:
   - **TP（Take Profit）**: +x_tick で利確
   - **SL（Stop Loss）**: -y_tick で損切
   - **TO（Timeout）**: max_hold_bars 経過で強制決済

### パラメータ

- `--k-tick`: 反応帯幅（デフォルト: 5.0）
- `--x-tick`: 利確幅（デフォルト: 10.0）
- `--y-tick`: 損切幅（デフォルト: 5.0）
- `--max-hold-bars`: 最大保有期間（デフォルト: 60）
- `--strength-threshold`: レベル強度閾値（デフォルト: 0.5）

## 📉 バックテスト結果

### 出力ファイル

#### `backtest_summary.json`
```json
{
  "total_trades": 3577,
  "wins": 2075,
  "losses": 1502,
  "win_rate": 0.58,
  "avg_pnl_tick": -6.04,
  "total_pnl_tick": -21591.2,
  "max_dd_tick": -30476.8,
  "avg_hold_bars": 1.58
}
```

#### `trades.csv`
各トレードの詳細（エントリー/エグジット時刻、価格、PnL、保有期間、決済理由等）

### 評価指標

- **total_trades**: 総トレード数
- **wins / losses**: 勝ちトレード / 負けトレード
- **win_rate**: 勝率
- **avg_pnl_tick**: 平均損益（tick単位）
- **total_pnl_tick**: 累積損益
- **max_dd_tick**: 最大ドローダウン
- **avg_hold_bars**: 平均保有期間

## 🎨 可視化

### LOBタイムライン
- Mid価格の時系列
- Spreadの時系列

### OHLC + レベル線
- 分足終値ライン
- 各種サポレジレベルを水平線で表示（強度に応じて線の太さ/透明度が変化）

## ⚙️ 依存ライブラリ

```
pandas
numpy
matplotlib
```

## 🔧 カスタマイズ

### パラメータ最適化

銘柄ごとに最適なパラメータをグリッドサーチで探索：

```bash
# 単一銘柄の最適化
python optimize_params.py --lob-features output/lob_features.csv \
  --levels output/levels_by_symbol.jsonl \
  --symbol 6526.0 \
  --out output/optimized_params_6526.json

# 全銘柄の最適化
python optimize_params.py --lob-features output/lob_features.csv \
  --levels output/levels_by_symbol.jsonl \
  --out output/optimized_params_all.json
```

最適化対象パラメータ：
- `k_tick`: [3.0, 5.0, 7.0, 10.0]
- `x_tick`: [5.0, 10.0, 15.0, 20.0]
- `y_tick`: [3.0, 5.0, 7.0, 10.0]
- `max_hold_bars`: [30, 45, 60, 90, 120]

評価指標：
- 総PnL（主要指標）
- 勝率
- 最大ドローダウン（ペナルティ）
- タイムアウト率（ペナルティ）

### 設定管理（config.py）

パラメータ、銘柄別設定、除外銘柄の一元管理：

```python
# デフォルトパラメータ
DEFAULT_PARAMS = {
    "k_tick": 5.0,
    "x_tick": 10.0,
    "y_tick": 5.0,
    "max_hold_bars": 60,
    ...
}

# 銘柄別パラメータ（最適化結果を反映）
SYMBOL_PARAMS = {
    "6526.0": {
        "k_tick": 5.0,
        "x_tick": 5.0,
        "y_tick": 5.0,
        "max_hold_bars": 120,
        ...
    },
    ...
}

# 除外銘柄リスト（低勝率）
EXCLUDED_SYMBOLS = []
```

### パラメータチューニング

```bash
python main.py --phase all \
  --roll-n 30 \
  --k-depth 10 \
  --k-tick 3.0 \
  --x-tick 15.0 \
  --y-tick 7.5 \
  --max-hold-bars 120 \
  --strength-threshold 0.7
```

### 分足の変更

```bash
python ohlc_from_rss.py --rss input/rss_market_data.csv --out output/ohlc_5min.csv --freq 5min
```

## 📝 注意事項

1. **データ形式**: MS2 RSS生CSVを前提（時刻列: `記録日時`、板: `最良売気配値1..10` 等）
2. **文字コード**: UTF-8/CP932自動判定
3. **欠損処理**: 時刻・価格がNaNの行は除外
4. **ゼロ割**: 分母が0の場合はNaNを返す
5. **時系列**: 常に昇順ソート
6. **銘柄分離**: バックテストは銘柄ごとに独立して実行
7. **データ検証**: validation.pyによる入力データの整合性チェック

## 🐛 トラブルシューティング

### 「symbol列が見つからない」エラー
- LOB特徴量CSVに`symbol`列が含まれているか確認
- `lob_features.py`でsymbol列が追加されているか確認

### 「No valid parameter combination found」エラー
- `run_backtest_single_symbol()`の引数が正しいか確認
- `FIXED_PARAMS`に不要なパラメータが含まれていないか確認

### タイムアウト率が90%以上
- `max_hold_bars`を増やす（60 → 120）
- `x_tick`, `y_tick`を小さくして利確条件を緩和

### 勝率が10%以下
- 当該銘柄を`EXCLUDED_SYMBOLS`に追加
- パラメータ最適化を再実行

## 📊 パフォーマンス改善履歴

### v1.0 → v2.0 (2026-01)
- **問題**: 7銘柄が混在して処理され、銘柄ごとの特性が無視されていた
- **修正**: 銘柄ごとに分離してバックテスト実行
- **結果**: -103.6 tick → +159.4 tick（+263 tick改善）

主な変更：
1. config.py: パラメータ・除外銘柄の一元管理
2. validation.py: データ検証機能の追加
3. optimize_params.py: グリッドサーチによるパラメータ最適化
4. 銘柄別最適化: 各銘柄に最適なパラメータを設定
   - 6526.0: +60.5 tick（勝率35.2%）
   - 9501.0/9509.0/5016.0: +21-22 tick
   - 215A: +12.5 tick
   - 3350.0: +21.5 tick

## 🚧 今後の拡張

- [ ] 機械学習によるエントリータイミング改善
- [ ] リスク管理（建玉上限、連敗ストップ、時間帯フィルタ）
- [ ] 手数料・スリッページモデルの精緻化
- [ ] リアルタイムストリーミング対応
- [ ] Optunaによるベイズ最適化

## 📖 関連ドキュメント

- [Algo_Dev_Spec.md](Algo_Dev_Spec.md): 詳細な開発仕様書

## 📄 ライセンス

本プロジェクトは社内利用を想定しています。
