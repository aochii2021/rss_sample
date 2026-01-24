#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
結果書き込みモジュール

バックテスト結果（trades.csv, summary.json, levels.jsonl）の出力を管理
"""
import logging
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import json

logger = logging.getLogger(__name__)


class ResultWriter:
    """
    バックテスト結果の書き込みクラス
    
    trades.csv, summary.json, levels.jsonlを出力し、
    設定スナップショットを保存する。
    """
    
    def __init__(self, output_dir: Path):
        """
        初期化
        
        Args:
            output_dir: 出力ディレクトリ
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def write_trades(self, trades_df: pd.DataFrame) -> Path:
        """
        トレード結果をCSVで出力
        
        Args:
            trades_df: トレード結果のDataFrame
            
        Returns:
            出力ファイルパス
        """
        output_path = self.output_dir / "trades.csv"
        trades_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"トレード結果を出力: {output_path} ({len(trades_df)}件)")
        return output_path
    
    def write_summary(self, metrics: Dict[str, Any]) -> Path:
        """
        評価指標サマリをJSONで出力
        
        Args:
            metrics: 評価指標の辞書
            
        Returns:
            出力ファイルパス
        """
        output_path = self.output_dir / "summary.json"
        
        # メトリクスを出力用に整形（float64等をfloatに変換）
        formatted_metrics = self._format_metrics(metrics)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(formatted_metrics, f, ensure_ascii=False, indent=2)
        
        logger.info(f"サマリを出力: {output_path}")
        return output_path
    
    def write_levels(self, levels: List[Dict[str, Any]]) -> Path:
        """
        レベル情報をJSONL（JSON Lines）形式で出力
        
        Args:
            levels: レベル辞書のリスト
            
        Returns:
            出力ファイルパス
        """
        output_path = self.output_dir / "levels.jsonl"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for level in levels:
                # 各レベルを1行のJSONとして書き込み
                formatted_level = self._format_level(level)
                f.write(json.dumps(formatted_level, ensure_ascii=False) + '\n')
        
        logger.info(f"レベル情報を出力: {output_path} ({len(levels)}個)")
        return output_path
    
    def write_symbol_summary(self, trades_df: pd.DataFrame) -> Path:
        """
        銘柄別サマリをCSVで出力
        
        Args:
            trades_df: トレード結果のDataFrame
            
        Returns:
            出力ファイルパス
        """
        if 'symbol' not in trades_df.columns or len(trades_df) == 0:
            logger.warning("銘柄別サマリをスキップ: symbolカラムなしまたはデータなし")
            return None
        
        # 銘柄別に集計
        symbol_summary = trades_df.groupby('symbol').agg({
            'pnl_tick': ['count', 'sum', 'mean'],
            'hold_bars': 'mean'
        }).reset_index()
        
        # カラム名を整形
        symbol_summary.columns = ['symbol', 'trades', 'total_pnl', 'avg_pnl', 'avg_hold_bars']
        
        # 勝率を計算
        wins_by_symbol = trades_df[trades_df['pnl_tick'] > 0].groupby('symbol').size()
        symbol_summary['win_rate'] = symbol_summary.apply(
            lambda row: wins_by_symbol.get(row['symbol'], 0) / row['trades'] if row['trades'] > 0 else 0,
            axis=1
        )
        
        # ソート（合計損益の降順）
        symbol_summary = symbol_summary.sort_values('total_pnl', ascending=False)
        
        output_path = self.output_dir / "symbol_summary.csv"
        symbol_summary.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"銘柄別サマリを出力: {output_path}")
        return output_path
    
    def write_exit_reason_summary(self, trades_df: pd.DataFrame) -> Path:
        """
        決済理由別サマリをCSVで出力
        
        Args:
            trades_df: トレード結果のDataFrame
            
        Returns:
            出力ファイルパス
        """
        if 'exit_reason' not in trades_df.columns or len(trades_df) == 0:
            logger.warning("決済理由別サマリをスキップ: exit_reasonカラムなしまたはデータなし")
            return None
        
        # 決済理由別に集計
        exit_summary = trades_df.groupby('exit_reason').agg({
            'pnl_tick': ['count', 'sum', 'mean'],
            'hold_bars': 'mean'
        }).reset_index()
        
        # カラム名を整形
        exit_summary.columns = ['exit_reason', 'count', 'total_pnl', 'avg_pnl', 'avg_hold_bars']
        
        # ソート（件数の降順）
        exit_summary = exit_summary.sort_values('count', ascending=False)
        
        output_path = self.output_dir / "exit_reason_summary.csv"
        exit_summary.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"決済理由別サマリを出力: {output_path}")
        return output_path
    
    def write_all(
        self,
        trades_df: pd.DataFrame,
        metrics: Dict[str, Any],
        levels: List[Dict[str, Any]]
    ) -> Dict[str, Path]:
        """
        全ての結果ファイルを一括出力
        
        Args:
            trades_df: トレード結果のDataFrame
            metrics: 評価指標の辞書
            levels: レベル辞書のリスト
            
        Returns:
            出力ファイルパスの辞書
        """
        output_files = {}
        
        # trades.csv
        output_files['trades'] = self.write_trades(trades_df)
        
        # summary.json
        output_files['summary'] = self.write_summary(metrics)
        
        # levels.jsonl
        output_files['levels'] = self.write_levels(levels)
        
        # symbol_summary.csv
        symbol_summary_path = self.write_symbol_summary(trades_df)
        if symbol_summary_path:
            output_files['symbol_summary'] = symbol_summary_path
        
        # exit_reason_summary.csv
        exit_reason_path = self.write_exit_reason_summary(trades_df)
        if exit_reason_path:
            output_files['exit_reason_summary'] = exit_reason_path
        
        logger.info(f"全ての結果を出力完了: {self.output_dir}")
        return output_files
    
    def _format_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        メトリクスを出力用に整形
        
        Args:
            metrics: 元のメトリクス辞書
            
        Returns:
            整形されたメトリクス辞書
        """
        formatted = {}
        for key, value in metrics.items():
            if isinstance(value, (int, float, str, bool, type(None))):
                formatted[key] = value
            elif hasattr(value, 'item'):  # numpy types
                formatted[key] = value.item()
            elif isinstance(value, dict):
                formatted[key] = self._format_metrics(value)
            else:
                formatted[key] = str(value)
        return formatted
    
    def _format_level(self, level: Dict[str, Any]) -> Dict[str, Any]:
        """
        レベルを出力用に整形
        
        Args:
            level: 元のレベル辞書
            
        Returns:
            整形されたレベル辞書
        """
        formatted = {}
        for key, value in level.items():
            if key == 'timestamp' and hasattr(value, 'isoformat'):
                # datetimeをISO 8601形式の文字列に変換
                formatted[key] = value.isoformat()
            elif isinstance(value, (int, float, str, bool, type(None))):
                formatted[key] = value
            elif hasattr(value, 'item'):  # numpy types
                formatted[key] = value.item()
            elif isinstance(value, dict):
                formatted[key] = self._format_level(value)
            elif isinstance(value, list):
                formatted[key] = [
                    self._format_level(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                formatted[key] = str(value)
        return formatted


# テストハーネス
if __name__ == "__main__":
    import sys
    from pathlib import Path
    from datetime import datetime
    
    # パス設定
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    print("\n=== ResultWriter テスト ===\n")
    
    # テスト用出力ディレクトリ
    test_output_dir = Path("output") / "test_result_writer"
    writer = ResultWriter(test_output_dir)
    
    # テストデータ: トレード結果
    test_trades = pd.DataFrame({
        'entry_ts': [datetime(2026, 1, 20, 9, 30), datetime(2026, 1, 20, 10, 0)],
        'exit_ts': [datetime(2026, 1, 20, 9, 45), datetime(2026, 1, 20, 10, 30)],
        'symbol': ['215A', '3350'],
        'direction': ['buy', 'sell'],
        'entry_price': [1350.0, 550.0],
        'exit_price': [1360.0, 545.0],
        'pnl_tick': [10.0, 5.0],
        'hold_bars': [15, 30],
        'exit_reason': ['TP', 'TP'],
        'level': [1340.0, 560.0]
    })
    
    # テストデータ: 評価指標
    test_metrics = {
        'total_trades': 2,
        'wins': 2,
        'losses': 0,
        'win_rate': 1.0,
        'avg_pnl_tick': 7.5,
        'total_pnl_tick': 15.0,
        'max_dd_tick': 0.0,
        'avg_hold_bars': 22.5,
        'exit_reasons': {'TP': 2}
    }
    
    # テストデータ: レベル
    test_levels = [
        {
            'kind': 'psychological',
            'symbol': '215A',
            'level_now': 1300.0,
            'strength': 0.8,
            'timestamp': datetime(2026, 1, 19),
            'meta': {'round_to': 100}
        },
        {
            'kind': 'consolidation',
            'symbol': '3350',
            'level_now': 546.5,
            'strength': 1.0,
            'timestamp': datetime(2026, 1, 19),
            'meta': {'lookback_days': 60}
        }
    ]
    
    # 全ファイルを出力
    output_files = writer.write_all(test_trades, test_metrics, test_levels)
    
    print("\n=== 出力ファイル ===")
    for name, path in output_files.items():
        print(f"  {name}: {path}")
    
    # 出力内容を検証
    print("\n=== trades.csv (先頭5行) ===")
    trades_check = pd.read_csv(output_files['trades'], encoding='utf-8-sig')
    print(trades_check.head())
    
    print("\n=== summary.json ===")
    with open(output_files['summary'], 'r', encoding='utf-8') as f:
        summary_check = json.load(f)
        print(json.dumps(summary_check, indent=2, ensure_ascii=False))
    
    print("\n=== levels.jsonl (先頭2行) ===")
    with open(output_files['levels'], 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 2:
                break
            level_check = json.loads(line)
            print(json.dumps(level_check, indent=2, ensure_ascii=False))
    
    print("\n✓ ResultWriter テスト完了")
