#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
統合バックテストシステム - メインエントリーポイント

設定ファイルベースで以下を実行:
1. データ読み込み（データリーク防止）
2. S/Rレベル生成（ON/OFF制御）
3. バックテスト実行
4. 結果出力（タイムスタンプ付きディレクトリ）

使用例:
    python main.py
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from dataclasses import asdict

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from utils.config_validator import ConfigValidator, ConfigValidationError
from utils.date_utils import DateUtils
from utils.output_utils import OutputManager
from config.trade_params import get_params, is_excluded
from core.data_loader import DataLoader
from core.level_generator import LevelGenerator
from processors.lob_processor import LOBProcessor
from processors.ohlc_processor import OHLCProcessor
from core.strategy import CounterTradeStrategy, Position
from core.backtest_engine import BacktestEngine
from core.entry_filter import EnvironmentFilter, EnvFilterThresholds
from output_handlers.result_writer import ResultWriter
from output_handlers.visualizer import Visualizer
import pandas as pd

logger = logging.getLogger(__name__)


def _normalize_symbol(symbol: str) -> str:
    """
    銘柄コードを正規化（.0を削除）
    
    Args:
        symbol: 銘柄コード
        
    Returns:
        正規化された銘柄コード
    """
    s = str(symbol)
    if s.endswith('.0'):
        return s[:-2]
    return s


class UnifiedBacktest:
    """統合バックテストシステム"""
    
    def __init__(self, base_dir: Path = None):
        """
        初期化
        
        Args:
            base_dir: ベースディレクトリ（デフォルトはalgo4_counter_trade配下）
        """
        # algo4_counter_tradeディレクトリに固定
        self.base_dir = Path(__file__).parent
        self.backtest_config: Dict[str, Any] = {}
        self.level_config: Dict[str, Any] = {}
        self.output_manager: OutputManager = None
        self.data_loader: DataLoader = None
        self.level_generator: LevelGenerator = None
        self.lob_processor: LOBProcessor = None
        self.ohlc_processor: OHLCProcessor = None
        
    def load_configs(self) -> None:
        """設定ファイルをロード・検証"""
        logger.info("=" * 60)
        logger.info("設定ファイル読み込み開始")
        logger.info("=" * 60)
        
        try:
            # バックテスト設定
            self.backtest_config = ConfigValidator.load_backtest_config(
                str(self.base_dir / "config" / "backtest_config.yaml")
            )
            logger.info(f"✓ バックテスト設定: mode={self.backtest_config['mode']}")
            logger.info(
                f"  期間: {self.backtest_config['backtest']['start_date']} ～ "
                f"{self.backtest_config['backtest']['end_date']}"
            )
            
            # レベル設定
            self.level_config = ConfigValidator.load_level_config(
                str(self.base_dir / "config" / "level_config.yaml")
            )
            enabled_types = ConfigValidator.get_enabled_level_types(self.level_config)
            logger.info(f"✓ レベル設定: 有効タイプ={enabled_types}")
            
            # データパス検証
            ConfigValidator.validate_data_paths(self.backtest_config, self.base_dir)
            logger.info("✓ データパス検証完了")
            
            # コンポーネント初期化
            self.data_loader = DataLoader(
                chart_data_dir=str(self.base_dir / self.backtest_config['data']['chart_data_dir']),
                market_data_dir=str(self.base_dir / self.backtest_config['data']['market_data_dir'])
            )
            logger.info("✓ DataLoader初期化完了")
            
            self.level_generator = LevelGenerator(level_config=self.level_config)
            logger.info("✓ LevelGenerator初期化完了")
            
            self.lob_processor = LOBProcessor()
            logger.info("✓ LOBProcessor初期化完了")
            
            self.ohlc_processor = OHLCProcessor()
            logger.info("✓ OHLCProcessor初期化完了")
            
        except ConfigValidationError as e:
            logger.error(f"設定ファイルエラー: {e}")
            raise
        except Exception as e:
            logger.error(f"予期しないエラー: {e}")
            raise
    
    def setup_output(self) -> None:
        """出力ディレクトリとロギングを設定"""
        logger.info("=" * 60)
        logger.info("出力環境セットアップ")
        logger.info("=" * 60)
        
        # OutputManager初期化
        output_base = self.backtest_config['data']['runs_base_dir']
        self.output_manager = OutputManager(output_base)
        
        # タイムスタンプ付きディレクトリ作成
        output_format = self.backtest_config['output'].get('run_dir_format', '%Y%m%d_%H%M%S')
        output_dir = self.output_manager.create_timestamped_output_dir(output_format)
        
        # ロギング再設定（ファイル出力追加）
        log_config = self.backtest_config.get('logging', {})
        self.output_manager.setup_logging(
            log_level=log_config.get('level', 'INFO'),
            log_to_file=log_config.get('log_file', True),
            log_file_name='backtest.log'
        )
        
        logger.info(f"✓ 出力ディレクトリ: {output_dir}")
        
        # 設定スナップショット保存
        self.output_manager.save_config_snapshot(
            self.backtest_config,
            self.level_config
        )
        logger.info("✓ 設定スナップショット保存完了")
        
        # target_symbols.csvをinput/に保存
        self._save_target_symbols_snapshot()
    
    def _save_target_symbols_snapshot(self) -> None:
        """target_symbols.csvのスナップショットを保存"""
        import shutil
        
        source_path = self.base_dir / "config" / "target_symbols.csv"
        if source_path.exists():
            input_dir = self.output_manager.current_output_dir / "input"
            input_dir.mkdir(parents=True, exist_ok=True)
            dest_path = input_dir / "target_symbols.csv"
            shutil.copy2(source_path, dest_path)
            logger.info(f"✓ 対象銘柄リスト保存: {dest_path}")
        else:
            logger.warning(f"target_symbols.csvが見つかりません: {source_path}")
    
    def phase1_load_data(self, target_date: datetime) -> Dict[str, Any]:
        """
        Phase 1: データ読み込み（データリーク防止）
        
        Args:
            target_date: バックテスト対象日
            
        Returns:
            ロードしたデータ辞書 {'chart_data': dict, 'market_data': dict}
        """
        logger.info("-" * 60)
        logger.info(f"Phase 1: データ読み込み - {target_date.strftime('%Y-%m-%d')}")
        logger.info("-" * 60)
        
        # チャートデータ読み込み（target_date以前のデータのみ）
        chart_data = self.data_loader.load_chart_data_until(target_date)
        logger.info(f"✓ チャートデータ読み込み完了: {len(chart_data)}銘柄")
        for symbol, df in chart_data.items():
            logger.info(f"  - {symbol}: {len(df)}行")
        
        # 板情報データ読み込み（target_date当日のみ）
        market_data = self.data_loader.load_market_data_for_date(target_date)
        logger.info(f"✓ 板情報データ読み込み完了: {len(market_data)}銘柄")
        for symbol, df in market_data.items():
            logger.info(f"  - {symbol}: {len(df)}行")
        
        return {
            'chart_data': chart_data,
            'market_data': market_data
        }
    
    def phase2_generate_levels(
        self,
        target_date: datetime,
        chart_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Phase 2: S/Rレベル生成
        
        Args:
            target_date: バックテスト対象日
            chart_data: チャートデータ辞書 {symbol: df}
            
        Returns:
            生成されたレベル辞書 {symbol: [level_dict, ...]}
        """
        logger.info("-" * 60)
        logger.info(f"Phase 2: レベル生成 - {target_date.strftime('%Y-%m-%d')}")
        logger.info("-" * 60)
        
        enabled_types = ConfigValidator.get_enabled_level_types(self.level_config)
        logger.info(f"有効なレベルタイプ: {enabled_types}")
        
        # OHLCデータ生成（MA等に必要）
        # OHLCProcessorは辞書を期待するため、チャートデータが空なら空の辞書を渡す
        ohlc_data = {}
        if chart_data:
            # ここではチャートデータをそのまま渡す（DataLoader出力がすでに適切な形式のため）
            ohlc_data = chart_data  # 一旦そのまま渡してみる
        
        # レベル生成
        all_levels = self.level_generator.generate(
            target_date=target_date,
            chart_data=chart_data,
            ohlc_data=ohlc_data
        )
        
        # サマリ出力
        total_levels = sum(len(levels) for levels in all_levels.values())
        logger.info(f"✓ レベル生成完了: {len(all_levels)}銘柄, 合計{total_levels}個")
        for symbol, levels in all_levels.items():
            logger.info(f"  - {symbol}: {len(levels)}個")
        
        return all_levels
    
    def phase3_process_lob_features(
        self,
        target_date: datetime,
        market_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        Phase 3: LOB特徴量計算
        
        Args:
            target_date: バックテスト対象日
            market_data: 板情報データ辞書 {symbol: df}
            
        Returns:
            LOB特徴量辞書 {symbol: df_with_features}
        """
        logger.info("-" * 60)
        logger.info(f"Phase 3: LOB特徴量計算 - {target_date.strftime('%Y-%m-%d')}")
        logger.info("-" * 60)
        
        # LOB特徴量計算（辞書を直接渡す）
        lob_features = self.lob_processor.process(market_data)
        
        logger.info(f"✓ LOB特徴量計算完了: {len(lob_features)}銘柄")
        for symbol, df in lob_features.items():
            logger.info(f"  - {symbol}: {len(df)}行")
        
        return lob_features
    
    def phase4_run_backtest(
        self,
        target_date: datetime,
        levels: Dict[str, List[Dict]],
        lob_features: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Phase 4: バックテスト実行
        
        Args:
            target_date: バックテスト対象日
            levels: S/Rレベル辞書 {symbol: [level_dict, ...]}
            lob_features: LOB特徴量辞書 {symbol: df}
            
        Returns:
            バックテスト結果 {'date': datetime, 'trades': list, 'levels': dict}
        """
        logger.info("-" * 60)
        logger.info(f"Phase 4: バックテスト実行 - {target_date.strftime('%Y-%m-%d')}")
        logger.info("-" * 60)
        
        if not lob_features:
            logger.warning("LOB特徴量データなし")
            return {'date': target_date, 'trades': [], 'levels': levels}
        
        # 全銘柄のLOB特徴量とレベルをマージ
        all_lob_rows = []
        all_levels_list = []
        
        for symbol, df in lob_features.items():
            norm_symbol = _normalize_symbol(symbol)
            if not df.empty:
                all_lob_rows.append(df)
            if norm_symbol in levels:
                all_levels_list.extend(levels[norm_symbol])
        
        if not all_lob_rows:
            logger.warning("有効なLOB特徴量データなし")
            return {'date': target_date, 'trades': [], 'levels': levels}
        
        # 全銘柄のDataFrameを結合
        lob_df = pd.concat(all_lob_rows, ignore_index=True)
        
        # Strategy初期化（デフォルトパラメータ使用）
        default_params = {
            'k_tick': 5.0,
            'x_tick': 10.0,
            'y_tick': 5.0,
            'max_hold_bars': 60,
            'strength_th': 0.5,
            'roll_n': 20,
            'k_depth': 5
        }
        strategy = CounterTradeStrategy(params=default_params)
        
        # 環境フィルタ設定（実験③：support距離緩和による機会増）
        # 理論: 板の厚み（買い板優勢）→ 逃げやすさ → 小負け削減
        filter_thresholds = EnvFilterThresholds(
            min_prev_day_volume_ratio_20d=1.07,
            min_prev_day_last30min_return=-0.0135,
            max_daily_support_dist_atr=0.025,  # 実験③: 0.02→0.025（機会増）
            board_indicator='micro_bias',  # 板バイアス（買い板/売り板の厚み比）
            board_window='10m',            # 寄り後10分窓（リークなし）
            min_board_threshold=-0.05,     # 固定（コア条件）
            entry_start_time='09:10:00'    # 9:10以降エントリー開始（窓整合）
        )
        env_filter = EnvironmentFilter(thresholds=filter_thresholds)
        logger.info(f"フィルタ設定: 板指標={filter_thresholds.board_indicator}, 窓={filter_thresholds.board_window}, 閾値={filter_thresholds.min_board_threshold}, エントリー開始={filter_thresholds.entry_start_time}")
        
        # BacktestEngine初期化して実行
        engine = BacktestEngine(strategy=strategy, env_filter=env_filter)
        trades_df = engine.run(
            lob_df=lob_df,
            levels=all_levels_list,
            symbol_params=None  # symbol_paramsはデフォルト使用
        )
        
        # 結果サマリ
        num_trades = len(trades_df) if not trades_df.empty else 0
        logger.info(f"✓ バックテスト完了: {num_trades}件のトレード")
        if not trades_df.empty:
            total_pnl = trades_df['pnl_tick'].sum()
            win_trades = len(trades_df[trades_df['pnl_tick'] > 0])
            win_rate = win_trades / num_trades * 100 if num_trades > 0 else 0
            logger.info(f"  - 合計損益: {total_pnl:+.1f} tick")
            logger.info(f"  - 勝率: {win_rate:.1f}%")
        
        return {
            'date': target_date,
            'trades_df': trades_df,  # DataFrameを返す
            'levels': levels
        }
    
    def phase5_save_results(self, all_results: List[Dict[str, Any]]) -> None:
        """
        Phase 5: 結果保存
        
        Args:
            all_results: 日次バックテスト結果のリスト
        """
        logger.info("-" * 60)
        logger.info("Phase 5: 結果保存")
        logger.info("-" * 60)
        
        # 全トレードDataFrameを集約
        all_trades_dfs = []
        all_levels = {}
        for daily_result in all_results:
            if not daily_result:
                continue
            if 'trades_df' in daily_result and not daily_result['trades_df'].empty:
                all_trades_dfs.append(daily_result['trades_df'])
            # レベルをマージ（銘柄ごとに統合）
            if 'levels' in daily_result:
                for symbol, levels in daily_result['levels'].items():
                    if symbol not in all_levels:
                        all_levels[symbol] = []
                    all_levels[symbol].extend(levels)
        
        # 全トレードDataFrameを結合
        trades_df = pd.concat(all_trades_dfs, ignore_index=True) if all_trades_dfs else pd.DataFrame()
        # symbol列をstr型・4桁ゼロ埋めで正規化
        if not trades_df.empty and 'symbol' in trades_df.columns:
            trades_df['symbol'] = trades_df['symbol'].apply(lambda s: str(int(float(s))).zfill(4) if str(s).replace('.0','').isdigit() else str(s))
            print('DEBUG: trades_df symbol dtype after normalization:', trades_df['symbol'].dtype)
            print('DEBUG: trades_df symbol unique after normalization:', trades_df['symbol'].unique())
        
        # 評価指標計算
        metrics = self._calculate_metrics(trades_df)
        
        # レベルをリストにフラット化
        levels_list = []
        for symbol, symbol_levels in all_levels.items():
            levels_list.extend(symbol_levels)
        
        # ResultWriter: ファイル出力（output/サブディレクトリに保存）
        output_dir = self.output_manager.get_output_dir()
        writer = ResultWriter(output_dir)
        writer.write_all(
            trades_df=trades_df,
            metrics=metrics,
            levels=levels_list
        )
        logger.info("✓ ResultWriter出力完了")
        
        # Visualizer: グラフ生成（output/サブディレクトリに保存）
        if not trades_df.empty:
            visualizer = Visualizer(output_dir)
            visualizer.plot_all(trades_df)
            logger.info("✓ Visualizer出力完了")
            
            # トレードチャート生成
            self._generate_trade_charts(trades_df, all_levels, visualizer)
        else:
            logger.warning("トレードなし: グラフ生成スキップ")
        
        # latestリンク/コピー作成
        self.output_manager.create_latest_link()
        logger.info("✓ 最新結果へのリンク作成完了")
    
    def _generate_trade_charts(
        self,
        trades_df: pd.DataFrame,
        all_levels: Dict[str, List[Dict]],
        visualizer: 'Visualizer'
    ) -> None:
        """
        銘柄別トレードチャートを生成
        
        Args:
            trades_df: 全トレードDataFrame
            all_levels: 銘柄別レベル辞書
            visualizer: Visualizerインスタンス
        """
        # 可視化範囲（バックテスト期間）を設定
        start_dt = pd.to_datetime(self.backtest_config['backtest']['start_date'])
        end_dt = pd.to_datetime(self.backtest_config['backtest']['end_date'])
        lookback_days = len(DateUtils.get_business_days_between(start_dt, end_dt))

        # トレードがあった銘柄を取得
        symbols_with_trades = trades_df['symbol'].unique()
        norm_symbols = [_normalize_symbol(s) for s in symbols_with_trades]
        logger.info(f"トレードチャート生成: {len(symbols_with_trades)}銘柄")

        # 可視化用チャートデータは板情報と同じ時間帯の分足系のみを読み込み、バックテスト期間の営業日分だけ取得
        # 可視化時は当日データを含めるため、cutoff_dateを1日進める
        cutoff_for_visualization = end_dt + pd.Timedelta(days=1)
        chart_data = self.data_loader.load_chart_data_until(
            cutoff_date=cutoff_for_visualization,
            lookback_days=lookback_days,
            symbols=norm_symbols,
            allowed_timeframes=['1M', '2M', '3M', '4M', '5M', '10M', '15M', '30M', '60M', '2H', '4H', '8H']
        )
        
        for symbol in symbols_with_trades:
            try:
                # その銘柄のトレードを抽出
                symbol_trades = trades_df[trades_df['symbol'] == symbol].copy()

                # 正規化されたシンボルでチャートデータを検索
                norm_symbol = _normalize_symbol(symbol)
                if norm_symbol in chart_data:
                    chart_df = chart_data[norm_symbol]
                elif symbol in chart_data:
                    chart_df = chart_data[symbol]
                else:
                    logger.warning(f"  {symbol}: チャートデータなし、スキップ")
                    continue

                # バックテスト期間に切り詰め（開始～終了当日まで）
                end_dt_exclusive = end_dt + pd.Timedelta(days=1)
                chart_df = chart_df[(chart_df['timestamp'] >= start_dt) & (chart_df['timestamp'] < end_dt_exclusive)]
                if chart_df.empty:
                    logger.warning(f"  {symbol}: 指定期間のチャートデータなし、スキップ")
                    continue
                
                # その銘柄のレベルを取得
                symbol_levels = all_levels.get(norm_symbol, [])
                
                # トレードチャート生成
                visualizer.plot_trade_chart(
                    symbol=symbol,
                    chart_df=chart_df,
                    trades_df=symbol_trades,
                    levels=symbol_levels
                )
                
            except Exception as e:
                logger.warning(f"  {symbol}: トレードチャート生成失敗 - {e}")
    
    def _calculate_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        評価指標計算
        
        Args:
            trades_df: トレードDataFrame
            
        Returns:
            評価指標辞書
        """
        if trades_df.empty:
            return {
                'total_trades': 0,
                'win_trades': 0,
                'loss_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'max_win': 0.0,
                'max_loss': 0.0,
                'profit_factor': 0.0,
                'avg_hold_time_minutes': 0.0
            }
        
        total_trades = len(trades_df)
        win_trades = len(trades_df[trades_df['pnl_tick'] > 0])
        loss_trades = len(trades_df[trades_df['pnl_tick'] <= 0])
        win_rate = win_trades / total_trades if total_trades > 0 else 0.0
        
        total_pnl = trades_df['pnl_tick'].sum()
        avg_pnl = trades_df['pnl_tick'].mean()
        
        wins = trades_df[trades_df['pnl_tick'] > 0]['pnl_tick']
        losses = trades_df[trades_df['pnl_tick'] <= 0]['pnl_tick']
        
        avg_win = wins.mean() if not wins.empty else 0.0
        avg_loss = losses.mean() if not losses.empty else 0.0
        max_win = wins.max() if not wins.empty else 0.0
        max_loss = losses.min() if not losses.empty else 0.0
        
        total_win = wins.sum() if not wins.empty else 0.0
        total_loss = abs(losses.sum()) if not losses.empty else 0.0
        profit_factor = total_win / total_loss if total_loss > 0 else 0.0
        
        # 保有時間計算
        if 'entry_ts' in trades_df.columns and 'exit_ts' in trades_df.columns:
            trades_df['entry_ts'] = pd.to_datetime(trades_df['entry_ts'])
            trades_df['exit_ts'] = pd.to_datetime(trades_df['exit_ts'])
            trades_df['hold_time_seconds'] = (trades_df['exit_ts'] - trades_df['entry_ts']).dt.total_seconds()
            avg_hold_time_minutes = trades_df['hold_time_seconds'].mean() / 60
        else:
            avg_hold_time_minutes = 0.0
        
        return {
            'total_trades': int(total_trades),
            'win_trades': int(win_trades),
            'loss_trades': int(loss_trades),
            'win_rate': float(win_rate),
            'total_pnl': float(total_pnl),
            'avg_pnl': float(avg_pnl),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'max_win': float(max_win),
            'max_loss': float(max_loss),
            'profit_factor': float(profit_factor),
            'avg_hold_time_minutes': float(avg_hold_time_minutes)
        }
    
    def run(self) -> None:
        """メインバックテスト実行"""
        try:
            # 設定ロード
            self.load_configs()
            
            # 出力セットアップ
            self.setup_output()
            
            logger.info("=" * 60)
            logger.info("バックテスト実行開始")
            logger.info("=" * 60)
            
            # バックテスト期間の営業日を取得
            start_date = datetime.strptime(
                self.backtest_config['backtest']['start_date'],
                '%Y-%m-%d'
            )
            end_date = datetime.strptime(
                self.backtest_config['backtest']['end_date'],
                '%Y-%m-%d'
            )
            business_days = DateUtils.get_business_days_between(start_date, end_date)
            
            logger.info(f"対象営業日: {len(business_days)}日")
            for day in business_days:
                logger.info(f"  - {day.strftime('%Y-%m-%d (%a)')}")
            
            # 全結果を集約
            all_results = []
            
            # 各営業日でバックテスト実行
            for target_date in business_days:
                logger.info("")
                logger.info("=" * 60)
                logger.info(f"処理開始: {target_date.strftime('%Y-%m-%d')}")
                logger.info("=" * 60)
                
                # Phase 1: データ読み込み
                data = self.phase1_load_data(target_date)
                if not data['chart_data'] and not data['market_data']:
                    logger.warning(f"データなし: {target_date.strftime('%Y-%m-%d')} スキップ")
                    continue
                
                # Phase 2: レベル生成
                levels = self.phase2_generate_levels(target_date, data['chart_data'])
                
                # Phase 3: LOB特徴量計算
                lob_features = self.phase3_process_lob_features(target_date, data['market_data'])
                
                # Phase 4: バックテスト実行
                daily_results = self.phase4_run_backtest(target_date, levels, lob_features)
                all_results.append(daily_results)
                
                logger.info(f"✓ {target_date.strftime('%Y-%m-%d')} 完了")
            
            # Phase 5: 結果保存
            self.phase5_save_results(all_results)
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("バックテスト完了")
            logger.info("=" * 60)
            logger.info(f"結果出力先: {self.output_manager.current_output_dir}")
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error("エラーが発生しました")
            logger.error("=" * 60)
            logger.exception(e)
            raise


def main():
    """エントリーポイント"""
    print("=" * 60)
    print("統合バックテストシステム")
    print("=" * 60)
    print()
    
    # 初期ロギング設定（コンソールのみ）
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    try:
        backtest = UnifiedBacktest()
        backtest.run()
        
        print()
        print("=" * 60)
        print("[SUCCESS] 正常終了")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print()
        print("=" * 60)
        print("[INTERRUPT] ユーザーによる中断")
        print("=" * 60)
        sys.exit(1)
        
    except Exception as e:
        print()
        print("=" * 60)
        print("[ERROR] エラー終了")
        print("=" * 60)
        print(f"エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
