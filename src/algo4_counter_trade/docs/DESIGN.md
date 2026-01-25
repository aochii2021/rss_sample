# DESIGN.md - 統合バックテストシステム設計書

統合バックテストシステム（algo4_counter_trade）のアーキテクチャと設計思想を説明します。

## 目次

1. [設計目標](#設計目標)
2. [アーキテクチャ概要](#アーキテクチャ概要)
3. [モジュール設計](#モジュール設計)
4. [データフロー](#データフロー)
5. [データリーク防止設計](#データリーク防止設計)
6. [拡張性と保守性](#拡張性と保守性)
7. [設計判断の記録](#設計判断の記録)

---

## 設計目標

### 1. 再現性（Reproducibility）

- **目標**: 同じ設定・データで実行すれば、常に同じ結果を得られる
- **実現方法**:
  - データリーク防止機能（未来データの厳密な排除）
  - タイムスタンプベースの営業日判定
  - 設定ファイルのスナップショット保存

### 2. 設定ベース（Configuration-Driven）

- **目標**: コード変更なしでパラメータ調整可能
- **実現方法**:
  - YAMLによる設定ファイル（backtest_config.yaml, level_config.yaml）
  - Pythonモジュールによる銘柄別パラメータ（trade_params.py）
  - レベルタイプのON/OFF制御

### 3. モジュール性（Modularity）

- **目標**: 各機能を独立したモジュールとして実装
- **実現方法**:
  - 単一責任原則（SRP）に基づくクラス設計
  - 依存性注入（DI）パターン
  - インターフェース分離

### 4. データリーク防止（No Data Leakage）

- **目標**: バックテスト中に未来のデータを一切使用しない
- **実現方法**:
  - カットオフ日（target_date）の厳密な管理
  - DataLoaderによる未来データチェック
  - 時系列順のデータ処理

### 5. 拡張性（Extensibility）

- **目標**: 新しいレベルタイプや戦略を容易に追加可能
- **実現方法**:
  - プラグイン可能なレベルジェネレーター
  - 戦略のインターフェース化
  - Processorの抽象化

---

## アーキテクチャ概要

### レイヤー構造

```
┌─────────────────────────────────────────────┐
│          main.py (Entry Point)              │
│  ┌───────────────────────────────────────┐  │
│  │    UnifiedBacktest (Orchestrator)     │  │
│  │  - run()                              │  │
│  │  - phase1_load_data()                 │  │
│  │  - phase2_generate_levels()           │  │
│  │  - phase3_process_lob_features()      │  │
│  │  - phase4_run_backtest()              │  │
│  │  - phase5_save_results()              │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
         ↓           ↓           ↓
┌────────────┐ ┌────────────┐ ┌────────────┐
│   Core     │ │ Processors │ │  Handlers  │
│            │ │            │ │            │
│ DataLoader │ │ LOBProc    │ │ ResultWrtr │
│ LevelGen   │ │ OHLCProc   │ │ Visualizer │
│ Strategy   │ │            │ │            │
│ BacktestEng│ │            │ │            │
└────────────┘ └────────────┘ └────────────┘
         ↓           ↓           ↓
┌────────────┐ ┌────────────┐ ┌────────────┐
│   Utils    │ │   Config   │ │   Output   │
│            │ │            │ │            │
│ DateUtils  │ │ YAML       │ │ CSV/JSON   │
│ Validation │ │ TradeParams│ │ PNG        │
│ OutputUtils│ │            │ │ Log        │
└────────────┘ └────────────┘ └────────────┘
```

### コンポーネント間の依存関係

```
UnifiedBacktest
 ├─ depends on → ConfigValidator
 ├─ depends on → DataLoader
 ├─ depends on → LevelGenerator
 ├─ depends on → LOBProcessor
 ├─ depends on → OHLCProcessor
 ├─ depends on → BacktestEngine
 │   └─ depends on → CounterTradeStrategy
 ├─ depends on → ResultWriter
 └─ depends on → Visualizer

DataLoader
 ├─ depends on → DateUtils
 └─ depends on → ValidationUtils

LevelGenerator
 ├─ depends on → PivotSRGenerator
 ├─ depends on → ConsolidationGenerator
 ├─ depends on → PsychologicalGenerator
 ├─ depends on → MA5Generator
 └─ depends on → MA25Generator

BacktestEngine
 ├─ depends on → CounterTradeStrategy
 └─ produces → List[Trade]

ResultWriter
 └─ depends on → OutputUtils

Visualizer
 └─ depends on → matplotlib
```

---

## モジュール設計

### 1. core/data_loader.py

**責任**: データの読み込みとデータリーク防止

#### クラス: DataLoader

```python
class DataLoader:
    def __init__(self, chart_data_dir: str, market_data_dir: str):
        """
        データローダーの初期化
        
        Args:
            chart_data_dir: チャートデータディレクトリ
            market_data_dir: 板情報ディレクトリ
        """
    
    def load_chart_data_until(
        self, 
        target_date: date, 
        lookback_days: int = 5
    ) -> Dict[str, pd.DataFrame]:
        """
        target_date以前のチャートデータを読み込む
        
        Args:
            target_date: カットオフ日
            lookback_days: 遡及日数
        
        Returns:
            {symbol: DataFrame} の辞書
        
        Raises:
            DataLeakError: 未来データが検出された場合
        """
    
    def load_market_data_for_date(
        self, 
        target_date: date
    ) -> Dict[str, pd.DataFrame]:
        """
        target_date当日の板情報を読み込む
        
        Args:
            target_date: 対象日
        
        Returns:
            {symbol: DataFrame} の辞書
        """
```

**設計判断**:
- `load_*_until` / `load_*_for_date` という命名で、時間的制約を明示
- 未来データチェックをDataLoader内部で実施（関心の分離）
- Dictによる柔軟なデータ構造（銘柄数が可変）

### 2. core/level_generator.py

**責任**: 複数のレベルタイプを統合的に生成

#### クラス: LevelGenerator

```python
class LevelGenerator:
    def __init__(self, level_config: dict):
        """
        レベルジェネレーターの初期化
        
        Args:
            level_config: レベル設定（level_config.yaml）
        """
    
    def generate(
        self, 
        chart_data: Dict[str, pd.DataFrame],
        ohlc_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, List[Level]]:
        """
        全レベルタイプを生成
        
        Args:
            chart_data: チャートデータ
            ohlc_data: OHLCデータ（板情報から生成）
        
        Returns:
            {symbol: [Level, ...]} の辞書
        """
```

**設計判断**:
- レベルタイプごとに個別のGeneratorクラスを持つ（OCP: Open-Closed Principle）
- enable/disableフラグによる柔軟な制御
- 強度（strength）による重要度の定量化

### 3. core/strategy.py

**責任**: エントリー・決済ロジックの実装

#### クラス: CounterTradeStrategy

```python
class CounterTradeStrategy:
    def __init__(self, params: dict):
        """
        逆張り戦略の初期化
        
        Args:
            params: パラメータ（k_tick, x_tick, y_tick, max_hold_bars）
        """
    
    def check_entry(
        self, 
        current_bar: pd.Series, 
        levels: List[Level]
    ) -> Optional[Position]:
        """
        エントリーシグナルをチェック
        
        Args:
            current_bar: 現在のバーデータ
            levels: 有効なレベルリスト
        
        Returns:
            Position（エントリーする場合）またはNone
        """
    
    def check_exit(
        self, 
        position: Position, 
        current_bar: pd.Series
    ) -> Optional[Tuple[str, float]]:
        """
        決済シグナルをチェック
        
        Args:
            position: 保有ポジション
            current_bar: 現在のバーデータ
        
        Returns:
            (exit_reason, exit_price) またはNone
        """
```

**設計判断**:
- Strategyをインターフェース化（将来的に複数戦略対応可能）
- `check_entry` / `check_exit` による明確な責任分離
- パラメータを外部から注入（DI）

### 4. core/backtest_engine.py

**責任**: バックテストの実行管理

#### クラス: BacktestEngine

```python
class BacktestEngine:
    def __init__(
        self, 
        strategy: CounterTradeStrategy,
        logger: Optional[logging.Logger] = None
    ):
        """
        バックテストエンジンの初期化
        
        Args:
            strategy: 戦略インスタンス
            logger: ロガー
        """
    
    def run(
        self, 
        lob_data: pd.DataFrame, 
        levels: List[Level],
        symbol: str
    ) -> pd.DataFrame:
        """
        シングルシンボルのバックテストを実行
        
        Args:
            lob_data: LOB特徴量データ
            levels: 使用するレベルリスト
            symbol: 銘柄コード
        
        Returns:
            トレード記録のDataFrame
        """
```

**設計判断**:
- バックテストエンジンは戦略に依存（Strategy Pattern）
- シングルシンボル単位で実行（並列化しやすい）
- 戻り値はDataFrame（集計しやすい）

### 5. processors/lob_processor.py

**責任**: 板情報から特徴量を計算

#### クラス: LOBProcessor

```python
class LOBProcessor:
    def __init__(self):
        """LOBプロセッサーの初期化"""
    
    def process(
        self, 
        market_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        板情報から特徴量を計算
        
        Args:
            market_data: {symbol: 板情報DataFrame}
        
        Returns:
            {symbol: 特徴量付きDataFrame}
        """
```

**計算される特徴量**:
- `spread`: スプレッド（ask1 - bid1）
- `mid_price`: ミッド価格（(ask1 + bid1) / 2）
- `micro_price`: マイクロ価格（加重平均）
- `bias`: バイアス（買い圧力 - 売り圧力）
- `ofi`: Order Flow Imbalance
- `depth_imbalance`: Depth Imbalance

**設計判断**:
- 特徴量計算をProcessorに集約（SRP）
- Dictベースの入出力（柔軟性）
- 欠損値処理を内部で実施

### 6. processors/ohlc_processor.py

**責任**: 板情報からOHLCを生成

#### クラス: OHLCProcessor

```python
class OHLCProcessor:
    def __init__(self, interval_minutes: int = 3):
        """
        OHLCプロセッサーの初期化
        
        Args:
            interval_minutes: リサンプリング間隔（分）
        """
    
    def process(
        self, 
        market_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        板情報からOHLCを生成
        
        Args:
            market_data: {symbol: 板情報DataFrame}
        
        Returns:
            {symbol: OHLC DataFrame}
        """
```

**設計判断**:
- レベル生成にチャートデータが不足している場合の補完用
- `mid_price`を使用してOHLC生成
- リサンプリング間隔は設定可能

### 7. output_handlers/result_writer.py

**責任**: 結果をファイルに出力

#### クラス: ResultWriter

```python
class ResultWriter:
    def __init__(self, output_dir: str, logger: Optional[logging.Logger] = None):
        """
        結果ライターの初期化
        
        Args:
            output_dir: 出力ディレクトリ
            logger: ロガー
        """
    
    def write_trades(self, trades_df: pd.DataFrame):
        """trades.csvを出力"""
    
    def write_summary(self, summary: dict):
        """summary.jsonを出力"""
    
    def write_levels(self, levels_dict: Dict[str, List[Level]]):
        """levels.jsonlを出力"""
    
    def write_symbol_summary(self, trades_df: pd.DataFrame):
        """symbol_summary.csvを出力"""
    
    def write_exit_reason_summary(self, trades_df: pd.DataFrame):
        """exit_reason_summary.csvを出力"""
```

**設計判断**:
- ファイル形式ごとにメソッドを分離（SRP）
- DataFrameからの集計処理を内包
- ファイル存在確認と上書き防止

### 8. output_handlers/visualizer.py

**責任**: グラフを生成

#### クラス: Visualizer

```python
class Visualizer:
    def __init__(self, output_dir: str, logger: Optional[logging.Logger] = None):
        """
        ビジュアライザーの初期化
        
        Args:
            output_dir: 出力ディレクトリ
            logger: ロガー
        """
    
    def plot_pnl_curve(self, trades_df: pd.DataFrame):
        """PnL曲線をプロット"""
    
    def plot_pnl_distribution(self, trades_df: pd.DataFrame):
        """PnL分布をプロット"""
    
    def plot_symbol_performance(self, trades_df: pd.DataFrame):
        """銘柄別パフォーマンスをプロット"""
    
    def plot_exit_reason_breakdown(self, trades_df: pd.DataFrame):
        """決済理由内訳をプロット"""
    
    def plot_hold_time_distribution(self, trades_df: pd.DataFrame):
        """保有時間分布をプロット"""
```

**設計判断**:
- グラフ種類ごとにメソッドを分離
- matplotlib使用（標準的）
- 日本語フォント対応

---

## データフロー

### 営業日ループ（外側）

```
for target_date in business_days:
    ↓
    Phase 1: データ読み込み
    ↓
    Phase 2: レベル生成
    ↓
    Phase 3: LOB特徴量計算
    ↓
    Phase 4: バックテスト実行
    ↓
    （次の営業日へ）
↓
Phase 5: 結果保存
```

### Phase 1: データ読み込み

```
target_date = 2026-01-19

DataLoader.load_chart_data_until(target_date, lookback_days=5)
  → チャートデータ: 2026-01-14 ～ 2026-01-19
  → 未来データチェック: OK

DataLoader.load_market_data_for_date(target_date)
  → 板情報: 2026-01-19 のみ
  → 未来データチェック: OK

返却: {
  chart_data: {symbol: DataFrame, ...},
  market_data: {symbol: DataFrame, ...}
}
```

### Phase 2: レベル生成

```
LevelGenerator.generate(chart_data, ohlc_data)
  ↓
  level_config.pivot_sr.enable == true?
    → PivotSRGenerator.generate(chart_data)
  ↓
  level_config.consolidation.enable == true?
    → ConsolidationGenerator.generate(chart_data)
  ↓
  level_config.psychological.enable == true?
    → PsychologicalGenerator.generate(chart_data)
  ↓
  level_config.ma5.enable == true?
    → MA5Generator.generate(chart_data)
  ↓
  level_config.ma25.enable == true?
    → MA25Generator.generate(chart_data)
  ↓
返却: {symbol: [Level, Level, ...], ...}
```

### Phase 3: LOB特徴量計算

```
LOBProcessor.process(market_data)
  ↓
  各銘柄について:
    - spread = ask1_price - bid1_price
    - mid_price = (ask1_price + bid1_price) / 2
    - micro_price = weighted average
    - bias = buy_pressure - sell_pressure
    - ofi = Order Flow Imbalance
    - depth_imbalance = Depth Imbalance
  ↓
返却: {symbol: DataFrame with features, ...}
```

### Phase 4: バックテスト実行

```
for symbol in symbols:
  ↓
  params = trade_params.get_params(symbol)
  ↓
  if trade_params.is_excluded(symbol):
    continue
  ↓
  strategy = CounterTradeStrategy(params)
  engine = BacktestEngine(strategy)
  ↓
  trades_df = engine.run(lob_data[symbol], levels[symbol], symbol)
  ↓
  all_trades.append(trades_df)
↓
返却: pd.concat(all_trades)
```

### Phase 5: 結果保存

```
ResultWriter.write_trades(all_trades_df)
ResultWriter.write_summary(summary)
ResultWriter.write_levels(all_levels)
ResultWriter.write_symbol_summary(all_trades_df)
ResultWriter.write_exit_reason_summary(all_trades_df)

Visualizer.plot_pnl_curve(all_trades_df)
Visualizer.plot_pnl_distribution(all_trades_df)
Visualizer.plot_symbol_performance(all_trades_df)
Visualizer.plot_exit_reason_breakdown(all_trades_df)
Visualizer.plot_hold_time_distribution(all_trades_df)
```

---

## データリーク防止設計

### 1. 時間的制約の徹底

**原則**: バックテスト実行時点（target_date）以降のデータは一切使用しない

#### 実装方法

```python
# DataLoader内部
def load_chart_data_until(self, target_date: date, lookback_days: int = 5):
    # 1. ファイル名からカットオフ日を抽出
    chart_dir = self._find_chart_dir_for_date(target_date)
    # "3M_3000_20260119" → cutoff_date = 2026-01-19
    
    # 2. データ読み込み
    df = pd.read_csv(chart_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 3. 未来データチェック
    if (df['timestamp'].dt.date > target_date).any():
        raise DataLeakError(f"未来データ検出: {symbol}")
    
    # 4. lookback_days 以内のデータのみ抽出
    start_date = target_date - timedelta(days=lookback_days * 2)  # 余裕を持たせる
    df = df[df['timestamp'].dt.date >= start_date]
    df = df[df['timestamp'].dt.date <= target_date]
    
    return df
```

### 2. 営業日の厳密な管理

**原則**: 営業日のみをバックテスト対象とする

#### 実装方法

```python
# utils/date_utils.py
def get_business_days(start_date: date, end_date: date) -> List[date]:
    """
    start_date ～ end_date の営業日リストを返す
    
    - 土日を除外
    - 祝日を除外（日本の祝日カレンダー）
    """
    business_days = []
    current = start_date
    
    while current <= end_date:
        if is_business_day(current):  # 土日祝を除外
            business_days.append(current)
        current += timedelta(days=1)
    
    return business_days
```

### 3. 設定スナップショットの保存

**原則**: 実行時の設定を記録し、再現可能性を確保

#### 実装方法

```python
# ResultWriter内部
def save_config_snapshots(self, backtest_config: dict, level_config: dict):
    """
    設定ファイルのスナップショットを保存
    """
    with open(self.output_dir / 'backtest_config_snapshot.yaml', 'w') as f:
        yaml.dump(backtest_config, f)
    
    with open(self.output_dir / 'level_config_snapshot.yaml', 'w') as f:
        yaml.dump(level_config, f)
```

---

## 拡張性と保守性

### 1. 新しいレベルタイプの追加

#### 手順

1. `core/level_generator.py` に新しいGeneratorクラスを追加

```python
class FibonacciGenerator:
    def __init__(self, config: dict):
        self.config = config
    
    def generate(self, chart_data: pd.DataFrame) -> List[Level]:
        # フィボナッチリトレースメントレベルを生成
        ...
```

2. `LevelGenerator` に統合

```python
class LevelGenerator:
    def generate(self, chart_data, ohlc_data):
        ...
        if self.level_config['level_types'].get('fibonacci', {}).get('enable', False):
            fib_gen = FibonacciGenerator(self.level_config['level_types']['fibonacci'])
            levels.extend(fib_gen.generate(chart_data[symbol]))
```

3. `config/level_config.yaml` に設定追加

```yaml
level_types:
  fibonacci:
    enable: true
    ratios: [0.236, 0.382, 0.5, 0.618, 0.786]
```

### 2. 新しい戦略の追加

#### 手順

1. `core/strategy.py` に新しいStrategyクラスを追加

```python
class MomentumStrategy:
    def __init__(self, params: dict):
        self.params = params
    
    def check_entry(self, current_bar, levels):
        # モメンタムベースのエントリーロジック
        ...
    
    def check_exit(self, position, current_bar):
        # 決済ロジック
        ...
```

2. `main.py` で戦略を選択

```python
if backtest_config['strategy']['type'] == 'counter_trade':
    strategy = CounterTradeStrategy(params)
elif backtest_config['strategy']['type'] == 'momentum':
    strategy = MomentumStrategy(params)
```

### 3. 新しい特徴量の追加

#### 手順

1. `processors/lob_processor.py` に計算ロジック追加

```python
class LOBProcessor:
    def process(self, market_data):
        ...
        # 新しい特徴量
        df['vwap'] = self._calculate_vwap(df)
        ...
```

---

## 設計判断の記録

### 1. なぜDictベースのデータ構造を採用したか？

**理由**:
- 銘柄数が可変（事前に固定できない）
- 銘柄ごとにデータ量が異なる
- 欠損銘柄（データがない銘柄）を柔軟に処理できる

**代替案**:
- ListベースのTupleリスト: `[(symbol, DataFrame), ...]`
  - 検索が線形時間（O(n)）
  - Dictはハッシュテーブル（O(1)）で高速

### 2. なぜDataFrameを使用するか？

**理由**:
- pandasの強力な時系列処理機能
- 欠損値処理、リサンプリング、集計が容易
- NumPyとの親和性（ベクトル化演算）

**代替案**:
- 独自のデータ構造: 実装コストが高く、再発明になる

### 3. なぜYAMLを設定ファイルに採用したか？

**理由**:
- 人間が読みやすい
- コメント対応
- Pythonの `PyYAML` でネイティブサポート

**代替案**:
- JSON: コメント不可、人間可読性が低い
- TOML: Pythonサポートが弱い

### 4. なぜレベルタイプごとにGeneratorを分離したか？

**理由**:
- 単一責任原則（SRP）
- テスト容易性（個別にテスト可能）
- 拡張性（新レベルタイプ追加が容易）

**代替案**:
- 1つのGeneratorクラスに全ロジックを実装: 肥大化、保守困難

### 5. なぜBacktestEngineとStrategyを分離したか？

**理由**:
- 戦略ロジックとバックテスト管理を分離（SRP）
- 複数戦略対応（Strategy Pattern）
- テスト容易性（Strategyを独立してテスト可能）

**代替案**:
- 統合クラス: 戦略変更のたびにBacktestEngine全体を書き換え

### 6. なぜOutputHandlerを2つに分けたか？

**理由**:
- ResultWriter: ファイル出力（CSV/JSON）
- Visualizer: グラフ出力（PNG）
- 責任を明確に分離（SRP）

**代替案**:
- 統合クラス: 複雑化、依存関係増加

---

## 今後の拡張計画

### 1. ライブトレード対応（Phase 12+）

- `mode: live` のサポート
- リアルタイムデータストリーム
- 発注APIとの統合

### 2. 並列化（Phase 12+）

- 銘柄ごとの並列バックテスト
- `multiprocessing` または `concurrent.futures`
- パフォーマンス改善

### 3. 最適化フレームワーク（Phase 12+）

- グリッドサーチ
- ベイズ最適化
- 遺伝的アルゴリズム

### 4. 機械学習統合（Phase 13+）

- レベル強度の学習
- エントリータイミングの予測
- 決済タイミングの最適化

---

## 参考資料

- **Design Patterns**: Gang of Four (GoF)
- **Clean Architecture**: Robert C. Martin
- **Python Best Practices**: PEP 8, PEP 257
- **Domain-Driven Design**: Eric Evans

---

## 変更履歴

### v1.0.0 (2026-01-24)
- 初版リリース
- モジュール構造確定
- データリーク防止設計確立
