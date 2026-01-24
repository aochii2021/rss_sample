#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
バックテストエンジン

CounterTradeStrategyを使用してバックテストを実行。
銘柄別パラメータ、取引セッション管理、結果集計機能を提供。
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys
import pandas as pd
import numpy as np

# パス設定
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.strategy import CounterTradeStrategy, Position

logger = logging.getLogger(__name__)


def _normalize_symbol(symbol: str) -> str:
    """
    銘柄コードを正規化（.0を削除）
    
    Args:
        symbol: 銘柄コード（例: "3350.0", "3350", "215A"）
    
    Returns:
        正規化された銘柄コード（例: "3350", "215A"）
    """
    s = str(symbol)
    if s.endswith('.0'):
        return s[:-2]
    return s


class BacktestEngine:
    """
    バックテストエンジンクラス
    
    複数銘柄に対してバックテストを実行し、トレード結果を返す。
    """
    
    def __init__(self, strategy: CounterTradeStrategy):
        """
        Args:
            strategy: CounterTradeStrategy instance
        """
        self.strategy = strategy
    
    def run(
        self,
        lob_df: pd.DataFrame,
        levels: List[Dict[str, Any]],
        symbol_params: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> pd.DataFrame:
        """
        バックテストを実行
        
        Args:
            lob_df: LOB特徴量データ（全銘柄）
            levels: S/Rレベルリスト（全銘柄）
            symbol_params: 銘柄別パラメータ（Noneの場合はデフォルトパラメータを使用）
            
        Returns:
            トレード結果のDataFrame
        """
        # レベルの強度フィルタリング
        valid_levels = [
            lv for lv in levels 
            if lv.get("strength", 0) >= self.strategy.strength_th
        ]
        
        all_trades = []
        
        # 銘柄別に処理
        if "symbol" in lob_df.columns:
            symbols = lob_df["symbol"].unique()
            logger.info(f"Backtesting {len(symbols)} symbols...")
            
            for symbol in symbols:
                # 銘柄データとレベルを抽出
                sym_df = lob_df[lob_df["symbol"] == symbol].copy().reset_index(drop=True)
                
                # 銘柄名を正規化して比較
                norm_symbol = _normalize_symbol(symbol)
                sym_levels = [
                    lv for lv in valid_levels 
                    if _normalize_symbol(lv.get("symbol", "")) == norm_symbol
                ]
                
                if len(sym_levels) == 0:
                    logger.info(f"  {symbol}: レベルなし、スキップ")
                    continue
                
                # 銘柄別パラメータがあれば使用（正規化されたsymbolで検索）
                if symbol_params and norm_symbol in symbol_params:
                    sym_strategy = CounterTradeStrategy(symbol_params[norm_symbol])
                    logger.info(f"  {symbol}: 銘柄別パラメータ使用")
                else:
                    sym_strategy = self.strategy
                
                # 銘柄ごとにバックテスト実行
                sym_trades = self.run_single_symbol(
                    sym_df, sym_levels, str(symbol), sym_strategy
                )
                all_trades.extend(sym_trades)
                logger.info(f"  {symbol}: {len(sym_trades)}件のトレード")
        else:
            # 銘柄列がない場合は全体で処理
            all_trades = self.run_single_symbol(
                lob_df, valid_levels, "", self.strategy
            )
        
        return pd.DataFrame(all_trades)
    
    def run_single_symbol(
        self,
        lob_df: pd.DataFrame,
        levels: List[Dict[str, Any]],
        symbol: str,
        strategy: CounterTradeStrategy
    ) -> List[Dict[str, Any]]:
        """
        単一銘柄のバックテスト
        
        Args:
            lob_df: LOB特徴量データ（単一銘柄）
            levels: S/Rレベルリスト（単一銘柄）
            symbol: 銘柄コード
            strategy: 使用する戦略インスタンス
            
        Returns:
            トレード記録のリスト
        """
        # レベルの統合（近い価格帯をまとめる）
        merged_levels = self.merge_nearby_levels(levels, tolerance=0.005)
        
        trades = []
        position: Optional[Position] = None
        current_session: Optional[str] = None
        
        for i, row in lob_df.iterrows():
            price = row["mid"]
            current_time = row["ts"]
            
            # セッション判定
            session = strategy.get_trading_session(current_time)
            session_changed = (current_session is not None and session != current_session)
            current_session = session
            
            # ポジション保有中の処理
            if position is not None:
                # セッション変更時は強制決済
                if session_changed or session == 'closed':
                    pnl_tick = self.calculate_pnl(position, price)
                    trades.append(self.create_trade_record(
                        position, row, price, pnl_tick, "SESSION_END"
                    ))
                    position = None
                    continue
                
                # 決済シグナルチェック
                exit_signal = strategy.check_exit_signal(
                    position, row, i, lob_df, merged_levels
                )
                
                if exit_signal.should_exit:
                    trades.append(self.create_trade_record(
                        position, row, price, exit_signal.pnl_tick, exit_signal.reason
                    ))
                    position = None
            
            # 新規エントリー判定
            can_enter = (
                session in ['morning', 'afternoon'] and 
                not strategy.is_session_end_approaching(current_time, session, minutes_before=5)
            )
            
            if position is None and can_enter:
                position = self.check_entry_opportunities(
                    row, i, merged_levels, strategy, symbol
                )
        
        # ループ終了時に持ち越しポジションを強制精算
        if position is not None:
            last_row = lob_df.iloc[-1]
            last_price = last_row["mid"]
            pnl_tick = self.calculate_pnl(position, last_price)
            trades.append(self.create_trade_record(
                position, last_row, last_price, pnl_tick, "EOD"
            ))
        
        return trades
    
    def check_entry_opportunities(
        self,
        row: pd.Series,
        idx: int,
        levels: List[Dict[str, Any]],
        strategy: CounterTradeStrategy,
        symbol: str
    ) -> Optional[Position]:
        """
        エントリー機会をチェック
        
        Args:
            row: 現在のLOBデータ行
            idx: 現在のインデックス
            levels: レベルリスト
            strategy: 戦略インスタンス
            symbol: 銘柄コード
            
        Returns:
            エントリーする場合はPositionインスタンス、しない場合はNone
        """
        price = row['mid']
        
        for level in levels:
            level_price = level['level_now']
            level_strength = level.get('strength', 1.0)
            level_count = level.get('merged_count', 1)
            
            # 買い逆張りチェック
            if price <= level_price + strategy.k_tick:
                if strategy.check_entry_signal(row, level_price, 'buy'):
                    return Position(
                        entry_idx=idx,
                        entry_price=price,
                        entry_ts=row['ts'],
                        direction='buy',
                        level=level_price,
                        level_strength=level_strength,
                        level_count=level_count,
                        symbol=symbol
                    )
            
            # 売り逆張りチェック
            if price >= level_price - strategy.k_tick:
                if strategy.check_entry_signal(row, level_price, 'sell'):
                    return Position(
                        entry_idx=idx,
                        entry_price=price,
                        entry_ts=row['ts'],
                        direction='sell',
                        level=level_price,
                        level_strength=level_strength,
                        level_count=level_count,
                        symbol=symbol
                    )
        
        return None
    
    def calculate_pnl(self, position: Position, exit_price: float) -> float:
        """
        損益を計算（tick単位）
        
        Args:
            position: ポジション
            exit_price: 決済価格
            
        Returns:
            損益（tick）
        """
        if position.direction == 'buy':
            return exit_price - position.entry_price
        else:
            return position.entry_price - exit_price
    
    def create_trade_record(
        self,
        position: Position,
        exit_row: pd.Series,
        exit_price: float,
        pnl_tick: float,
        exit_reason: str
    ) -> Dict[str, Any]:
        """
        トレード記録を作成
        
        Args:
            position: ポジション
            exit_row: 決済時のデータ行
            exit_price: 決済価格
            pnl_tick: 損益（tick）
            exit_reason: 決済理由
            
        Returns:
            トレード記録の辞書
        """
        hold_bars = exit_row.name - position.entry_idx if hasattr(exit_row, 'name') else 0
        
        return {
            "entry_ts": position.entry_ts,
            "exit_ts": exit_row['ts'],
            "symbol": position.symbol,
            "direction": position.direction,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "pnl_tick": pnl_tick,
            "hold_bars": hold_bars,
            "exit_reason": exit_reason,
            "level": position.level
        }
    
    def merge_nearby_levels(
        self,
        levels: List[Dict[str, Any]],
        tolerance: float = 0.005
    ) -> List[Dict[str, Any]]:
        """
        近い価格帯のレベルを統合し、strengthを加算
        
        Args:
            levels: レベルのリスト
            tolerance: 統合する価格の許容範囲（例: 0.005 = 0.5%）
            
        Returns:
            統合されたレベルのリスト
        """
        if not levels:
            return []
        
        # 価格でソート
        sorted_levels = sorted(levels, key=lambda x: x["level_now"])
        
        merged = []
        current_group = [sorted_levels[0]]
        
        for lv in sorted_levels[1:]:
            last_price = current_group[-1]["level_now"]
            current_price = lv["level_now"]
            
            # 価格が近い場合（tolerance以内）は同じグループに
            if abs(current_price - last_price) / last_price <= tolerance:
                current_group.append(lv)
            else:
                # グループを統合
                merged.append(self.merge_level_group(current_group))
                current_group = [lv]
        
        # 最後のグループを統合
        if current_group:
            merged.append(self.merge_level_group(current_group))
        
        return merged
    
    def merge_level_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        同じ価格帯のレベルを1つに統合
        
        Args:
            group: 統合するレベルのリスト
            
        Returns:
            統合されたレベル
        """
        if len(group) == 1:
            group[0]["merged_count"] = 1
            return group[0]
        
        # 加重平均で価格を計算（strengthで重み付け）
        total_strength = sum(lv.get("strength", 1.0) for lv in group)
        weighted_price = sum(
            lv["level_now"] * lv.get("strength", 1.0) for lv in group
        ) / total_strength
        
        # strengthを加算（上限2.0）
        combined_strength = min(2.0, total_strength)
        
        # ソース情報を結合
        sources = [lv.get("kind", "unknown") for lv in group]
        source_counts = {}
        for src in sources:
            source_counts[src] = source_counts.get(src, 0) + 1
        
        merged = {
            "level_now": weighted_price,
            "kind": group[0].get("kind", "support"),
            "symbol": group[0].get("symbol", ""),
            "strength": combined_strength,
            "merged_count": len(group),
            "meta": {
                "sources": source_counts,
                "original_prices": [lv["level_now"] for lv in group]
            }
        }
        
        return merged
    
    @staticmethod
    def calculate_metrics(trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        評価指標の計算
        
        Args:
            trades_df: トレード結果のDataFrame
            
        Returns:
            評価指標の辞書
        """
        if len(trades_df) == 0:
            return {"total_trades": 0}
        
        total = len(trades_df)
        wins = len(trades_df[trades_df["pnl_tick"] > 0])
        losses = len(trades_df[trades_df["pnl_tick"] < 0])
        win_rate = wins / total if total > 0 else 0.0
        
        avg_pnl = trades_df["pnl_tick"].mean()
        total_pnl = trades_df["pnl_tick"].sum()
        
        # 最大ドローダウン（簡易）
        cumsum = trades_df["pnl_tick"].cumsum()
        running_max = cumsum.expanding().max()
        dd = (cumsum - running_max).min()
        
        # 決済理由別の集計
        exit_reasons = trades_df['exit_reason'].value_counts().to_dict()
        
        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "avg_pnl_tick": avg_pnl,
            "total_pnl_tick": total_pnl,
            "max_dd_tick": dd,
            "avg_hold_bars": trades_df["hold_bars"].mean() if total > 0 else 0,
            "exit_reasons": exit_reasons
        }


# テストハーネス
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # パス設定
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from utils.config_validator import ConfigValidator
    from core.data_loader import DataLoader
    from core.level_generator import LevelGenerator
    from processors.lob_processor import LOBProcessor
    from config.trade_params import DEFAULT_PARAMS, SYMBOL_PARAMS
    from datetime import datetime, timedelta
    
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    print("\n=== BacktestEngine テスト ===\n")
    
    # 設定ロード
    config_validator = ConfigValidator()
    level_config = config_validator.load_level_config()
    
    # テスト用の対象日
    target_date = datetime(2026, 1, 20)
    
    # データロード
    data_loader = DataLoader(
        chart_data_dir="input/chart_data",
        market_data_dir="input/market_order_book",
        log_data_range=True,
        validate_no_future_data=True
    )
    
    chart_data = data_loader.load_chart_data_until(target_date, lookback_days=5)
    market_data = data_loader.load_market_data_for_date(target_date)
    
    # レベル生成
    level_generator = LevelGenerator(level_config)
    levels_dict = level_generator.generate(target_date, chart_data, {})
    
    # レベルをリスト形式に変換
    all_levels = []
    for symbol, symbol_levels in levels_dict.items():
        all_levels.extend(symbol_levels)
    
    # LOB特徴量生成
    lob_processor = LOBProcessor()
    lob_features = lob_processor.process(market_data)
    
    # LOB特徴量を単一DataFrameに統合
    lob_df_list = []
    for symbol, df in lob_features.items():
        df['symbol'] = symbol
        lob_df_list.append(df)
    lob_df = pd.concat(lob_df_list, ignore_index=True)
    
    # タイムスタンプ列をリネーム
    if 'timestamp' in lob_df.columns:
        lob_df.rename(columns={'timestamp': 'ts'}, inplace=True)
    
    print(f"LOB特徴量: {len(lob_df)}行, {len(lob_features)}銘柄")
    print(f"レベル: {len(all_levels)}個")
    
    # 戦略とエンジンの初期化
    strategy = CounterTradeStrategy(DEFAULT_PARAMS)
    engine = BacktestEngine(strategy)
    
    # バックテスト実行
    print("\nバックテスト実行中...")
    trades_df = engine.run(lob_df, all_levels, SYMBOL_PARAMS)
    
    print(f"\n=== バックテスト結果 ===")
    print(f"トレード件数: {len(trades_df)}件")
    
    if len(trades_df) > 0:
        # 評価指標の計算
        metrics = BacktestEngine.calculate_metrics(trades_df)
        
        print(f"\n勝率: {metrics['win_rate']:.2%}")
        print(f"平均損益: {metrics['avg_pnl_tick']:.2f} tick")
        print(f"合計損益: {metrics['total_pnl_tick']:.2f} tick")
        print(f"最大DD: {metrics['max_dd_tick']:.2f} tick")
        print(f"平均保有時間: {metrics['avg_hold_bars']:.1f} bars")
        
        print(f"\n決済理由:")
        for reason, count in metrics['exit_reasons'].items():
            print(f"  {reason}: {count}件")
        
        # 銘柄別サマリ
        print(f"\n銘柄別:")
        for symbol in trades_df['symbol'].unique():
            sym_trades = trades_df[trades_df['symbol'] == symbol]
            sym_pnl = sym_trades['pnl_tick'].sum()
            print(f"  {symbol}: {len(sym_trades)}件, 合計{sym_pnl:+.1f} tick")
    else:
        print("トレードなし")
