
# アルゴ開発仕様書（MS2直読：LOB特徴量 / サポレジ / 可視化 / 逆張り）

本書は、**マーケットスピードII（RSS）の生CSVを直接**利用して、  
1) LOB（板）特徴量、2) サポート/レジスタンス抽出、3) 可視化、4) 逆張り（ミーンリバージョン）アルゴ、を段階的に実装・拡張するための仕様です。  
GitHub Copilot によるコーディング支援を想定し、I/Oやインターフェースを明確に定義しています。

---

## 0. データ前提

### 0.1 MS2 RSS 生CSV（板）
- 時刻カラム（優先順）: `記録日時` → `現在値詳細時刻` → `現在値時刻`
- L1〜L10 価格・数量:
  - Ask: `最良売気配値1..10`, `最良売気配数量1..10`
  - Bid: `最良買気配値1..10`, `最良買気配数量1..10`
- 任意: `銘柄コード`（無い場合は空文字を許容）

### 0.2 OHLC（分足/日足）
- 列: `timestamp, open, high, low, close, volume`（CSV; pandas で読める形式）

---

## 1. LOB 特徴量（`lob_features_ms2.py`）

> 正規化なし（MS2列名を直接参照）。後日、標準スキーマ化する場合でも同じ特徴量定義を踏襲。

### 1.1 入出力
- **入力**: MS2 RSS 生CSV
- **出力**: 特徴量CSV（列）
  - `ts`（ISO時刻; 昇順ソート）
  - `symbol`（`銘柄コード`が無い場合は空文字）
  - `spread = Ask1_px - Bid1_px`
  - `mid = (Ask1_px + Bid1_px)/2`
  - `qi_l1 = (Bid1_qty - Ask1_qty) / (Bid1_qty + Ask1_qty)`
  - `microprice = (Ask1_px*Bid1_qty + Bid1_px*Ask1_qty)/(Bid1_qty + Ask1_qty)`
  - `micro_bias = microprice - mid`
  - `ofi_{N}`: Order Flow Imbalance の行数 N ローリング合計
  - `depth_imb_{k}`: 累積厚み差（L1..k）

### 1.2 数式定義
- Spread: `A1 - B1`
- Mid: `(A1 + B1)/2`
- QI: `(Bsz1 - Asz1) / (Bsz1 + Asz1)`
- Microprice / Micro-bias:
  - `microprice = (A1*Bsz1 + B1*Asz1) / (Bsz1 + Asz1)`
  - `micro_bias = microprice - mid`
- OFI（簡易・最良気配ベース）:
  - `ofi_inst = (1{ΔB1>0}*Bsz1 + 1{ΔB1=0}*ΔBsz1) - (1{ΔA1<0}*Asz1 + 1{ΔA1=0}*ΔAsz1)`
  - `ofi_N = rolling_sum(ofi_inst, N)`
- Depth Imbalance（〜k段）:
  - `depth_imb_k = Σ_{i=1..k} Bid_qty_i - Σ_{i=1..k} Ask_qty_i`

### 1.3 アルゴリズム仕様
- **時刻**: 候補列から選択 → `pd.to_datetime` でパース → 欠損除外 → **昇順ソート**
- **ゼロ割回避**: 分母が0のときは `NaN`
- **OFI**: 行数ベース `--roll-n`（時間窓は将来拡張）
- **L2〜k**: 存在列のみ合算

### 1.4 CLI
```bash
python alpha_kit/lob_features_ms2.py \
  --rss data/lob/rss_market_data.csv \
  --out out/lob_features.csv \
  --roll-n 20 \
  --k-depth 5
```

---

## 2. サポート/レジスタンス抽出（`sr_levels.py`）

### 2.1 出力フォーマット（JSONL, 1行＝1レベル）
```json
{
  "kind": "recent_low | recent_high | vpoc | hvn | swing_support | swing_resistance | prev_high | prev_low | prev_close",
  "anchors": [["ISO8601_ts", price], ["ISO8601_ts", price]],
  "slope": 0.0,
  "level_now": 1234.5,
  "strength": 0.0_to_1.0,
  "meta": {"lookback_bars": 180, "bin_size": 1, "day": "YYYY-MM-DD"}
}
```

### 2.2 ロジック
- **直近高安**（分足 `lookback_bars` 本）:
  - `recent_high = max(high)`, `recent_low = min(low)`
  - タッチ回数（閾値付近のヒット数）で強度補正
- **価格帯別出来高（VPOC/HVN）**（前日・前々日）:
  - 各バー出来高を `[low, high]` へ**均等配分**しヒスト化
  - VPOC = 最大ピーク, HVN = 上位ピーク群（上位3など）
  - 直近性（昨日 > 一昨日）で重み付け
- **スイングTL**（フラクタル）:
  - `left/right` 幅の谷/山を抽出 → 直近2点で線分化 → `slope` と `level_now` を算出
- **前日系**:
  - `prev_high / prev_low / prev_close` の水平線
- **強度正規化**:
  - 0–1 に線形正規化し、上位のみ採用可能（用途に応じてフィルタ）

### 2.3 CLI
```bash
# 分足のみ（VPOC/HVN/直近高安/スイング）
python alpha_kit/sr_levels.py \
  --min1 data/ohlc/minute.csv \
  --out out/levels.jsonl \
  --bin-size 1 --lookback-bars 180 --pivot-left 3 --pivot-right 3

# 日足のみ（前日系）
python alpha_kit/sr_levels.py \
  --day data/ohlc/daily.csv \
  --out out/levels.jsonl
```

---

## 3. 可視化（`viz_quicklook.py`）

### 3.1 LOB タイムライン（mid / spread）
- **入力**: MS2 生CSV（または正規化CSV）
- **描画**: 
  - `mid = (最良売気配値1 + 最良買気配値1)/2`
  - `spread = 最良売気配値1 - 最良買気配値1`

### 3.2 OHLC + レベル線
- **入力**: 分足CSV + 抽出レベルJSONL
- **描画**: 終値ライン + レベルを水平線表示（`anchors` 同時刻は水平）

### 3.3 例（擬似コード）
```python
# LOB
ts = ensure_ts(df)["ts"]
mid = (df["最良売気配値1"] + df["最良買気配値1"]) / 2.0
spr = df["最良売気配値1"] - df["最良買気配値1"]

plt.figure(figsize=(10,4)); plt.plot(ts, mid); plt.title("Mid"); plt.tight_layout()
plt.figure(figsize=(10,3)); plt.plot(ts, spr); plt.title("Spread"); plt.tight_layout()

# OHLC + Levels
plt.figure(figsize=(10,4)); plt.plot(df_min["timestamp"], df_min["close"], label="close")
for lv in levels:  # anchors or level_now を水平線で
    plt.axhline(lv["level_now"], linestyle="--", linewidth=1, alpha=0.8)
plt.legend(); plt.tight_layout()
```

---

## 4. 逆張り（ミーンリバージョン）アルゴ仕様

### 4.1 コンセプト
- **強いレベル帯**からの**乖離→戻り**を狙う。
- LOB の微視的バイアス（micro_bias / QI / OFI / depth_imb）で**反転の質**をフィルタ。

### 4.2 入力
- LOB特徴量CSV（1章の出力）
- S/RレベルJSONL（2章の出力）
- （任意）分足OHLC（検証用）

### 4.3 取引ルール（初期案）
**(A) 反応帯**: レベル `L` に対し `L ± k_tick` を反応帯に設定。  
**(B) シグナル**（戻りの兆候; いずれか満たす）:
- **micro_bias** の符号が戻り方向へ
- **OFI_N** が戻り方向で正（買い）/負（売り）
- **QI** が戻り方向へ
- **depth_imb_k** が戻り方向に有利
**(C) エントリー**
- 買い逆張り: `price ≤ L + k_tick` かつ (B) を満たす
- 売り逆張り: `price ≥ L - k_tick` かつ (B) を満たす
**(D) 手仕舞い**
- **TP**: `+x_tick`、**SL**: `-y_tick`、**TO**: 最大保有時間でクローズ
**(E) リスク**
- 同時建玉上限・連敗ストップ・時間帯フィルタ 等

### 4.4 パラメータ
- `k_tick`（反応帯幅）、`x_tick` / `y_tick`（利確/損切）
- `roll_n`（OFI窓）、`k_depth`（厚み集計段数）
- `strength` 閾値（レベル採用条件）

### 4.5 JOIN と評価（将来）
- 時系列整合: 分足終値時刻に丸め、LOB特徴量を `ffill` で合わせる
- 指標: 勝率、平均R、最大DD、保有時間、シグナル整合度（micro_bias/OFI/QI）
- コスト: 手数料 + スリッページ（保守的設定）

---

## 5. 実装ロードマップ（Copilot向け）

- [x] `lob_features_ms2.py`: Spread/Mid/QI/Microprice/Micro-bias/OFI/DepthImb
- [x] `sr_levels.py`: recent高安 / VPOC/HVN / スイングTL / 前日系 / 強度正規化
- [x] `viz_quicklook.py`: mid/spread・OHLC＋レベル
- [ ] 逆張り実験: 反応帯×LOB合流の売買検証スクリプト
- [ ] JOINユーティリティ: `symbol, ts` 粒度整合（floor/round/ffill）
- [ ] 指標集計: 勝率/平均R/最大DD/時間帯別
- [ ] ハイパラ探索: `k_tick, x_tick, y_tick, roll_n, k_depth, strength`

---

## 6. 付録：MS2 生CSV → 特徴量CSV（最小実行例）

```bash
python alpha_kit/lob_features_ms2.py \
  --rss data/lob/rss_market_data.csv \
  --out out/lob_features.csv \
  --roll-n 20 --k-depth 5
```

```bash
# 分足→サポレジ
python alpha_kit/sr_levels.py \
  --min1 data/ohlc/minute.csv \
  --out out/levels.jsonl \
  --bin-size 1 --lookback-bars 180 --pivot-left 3 --pivot-right 3
```

```bash
# 可視化（例）
python alpha_kit/viz_quicklook.py lob \
  --lob data/lob/rss_market_data.csv \
  --out out/figs/lob_mid_spread.png
```

---

## 7. テスト観点（最重要チェック）
- 文字コード（UTF-8/CP932）や列名揺れ（時刻列候補）に対する耐性
- `ts` 昇順・欠損除外の徹底
- 分母0の NaN 化、数量非負チェック
- OFIは累積和ベースで高速、L2集計は存在列のみ対象

---

本仕様に沿って、**MS2直読**での LOB 特徴量・S/R 抽出・可視化・逆張り検証を段階的に実装してください。将来、標準スキーマへ切替える場合でも、I/O定義を維持することで下流の互換性を確保できます。
