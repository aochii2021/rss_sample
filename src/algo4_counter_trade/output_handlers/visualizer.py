#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
結果可視化モジュール

バックテスト結果の可視化（PnL曲線、トレード分布、銘柄別パフォーマンス）
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # GUI不要のバックエンド
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 日本語フォント設定
plt.rcParams["font.sans-serif"] = ["Yu Gothic", "MS Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

logger = logging.getLogger(__name__)


class Visualizer:
    """
    バックテスト結果の可視化クラス
    
    PnL曲線、トレード分布、銘柄別パフォーマンス等のグラフを生成
    """
    
    def __init__(self, output_dir: Path):
        """
        初期化
        
        Args:
            output_dir: 出力ディレクトリ
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def plot_pnl_curve(self, trades_df: pd.DataFrame) -> Optional[Path]:
        """
        累積PnL曲線をプロット
        
        Args:
            trades_df: トレード結果のDataFrame
            
        Returns:
            出力ファイルパス
        """
        if len(trades_df) == 0:
            logger.warning("PnL曲線のプロットをスキップ: データなし")
            return None
        
        # タイムスタンプでソート
        trades_sorted = trades_df.sort_values('exit_ts').copy()
        trades_sorted['cumulative_pnl'] = trades_sorted['pnl_tick'].cumsum()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(trades_sorted['exit_ts'], trades_sorted['cumulative_pnl'], 
                linewidth=2, color='navy', label='累積PnL')
        ax.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        
        ax.set_xlabel('時刻')
        ax.set_ylabel('累積PnL (tick)')
        ax.set_title('累積PnL曲線')
        ax.legend()
        ax.grid(alpha=0.3)
        
        # 日時フォーマット
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        output_path = self.output_dir / "pnl_curve.png"
        plt.savefig(output_path, dpi=150)
        plt.close()
        
        logger.info(f"PnL曲線を出力: {output_path}")
        return output_path
    
    def plot_pnl_distribution(self, trades_df: pd.DataFrame) -> Optional[Path]:
        """
        PnL分布のヒストグラムをプロット
        
        Args:
            trades_df: トレード結果のDataFrame
            
        Returns:
            出力ファイルパス
        """
        if len(trades_df) == 0:
            logger.warning("PnL分布のプロットをスキップ: データなし")
            return None
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # ヒストグラム
        ax.hist(trades_df['pnl_tick'], bins=30, color='skyblue', 
                edgecolor='navy', alpha=0.7)
        ax.axvline(0, color='red', linestyle='--', linewidth=2, 
                   label='損益分岐点', alpha=0.7)
        
        # 平均値
        mean_pnl = trades_df['pnl_tick'].mean()
        ax.axvline(mean_pnl, color='green', linestyle='--', linewidth=2,
                   label=f'平均: {mean_pnl:.2f} tick', alpha=0.7)
        
        ax.set_xlabel('PnL (tick)')
        ax.set_ylabel('トレード件数')
        ax.set_title('PnL分布')
        ax.legend()
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        
        output_path = self.output_dir / "pnl_distribution.png"
        plt.savefig(output_path, dpi=150)
        plt.close()
        
        logger.info(f"PnL分布を出力: {output_path}")
        return output_path
    
    def plot_symbol_performance(self, trades_df: pd.DataFrame) -> Optional[Path]:
        """
        銘柄別パフォーマンスの棒グラフをプロット
        
        Args:
            trades_df: トレード結果のDataFrame
            
        Returns:
            出力ファイルパス
        """
        if 'symbol' not in trades_df.columns or len(trades_df) == 0:
            logger.warning("銘柄別パフォーマンスのプロットをスキップ: symbolカラムなしまたはデータなし")
            return None
        
        # 銘柄別に合計PnLを計算
        symbol_pnl = trades_df.groupby('symbol')['pnl_tick'].sum().sort_values(ascending=False)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 色分け（プラスは緑、マイナスは赤）
        colors = ['green' if pnl >= 0 else 'red' for pnl in symbol_pnl.values]
        
        ax.bar(range(len(symbol_pnl)), symbol_pnl.values, color=colors, alpha=0.7)
        ax.set_xticks(range(len(symbol_pnl)))
        ax.set_xticklabels(symbol_pnl.index, rotation=45, ha='right')
        
        ax.axhline(0, color='black', linewidth=1, alpha=0.5)
        ax.set_xlabel('銘柄')
        ax.set_ylabel('合計PnL (tick)')
        ax.set_title('銘柄別パフォーマンス')
        ax.grid(alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        output_path = self.output_dir / "symbol_performance.png"
        plt.savefig(output_path, dpi=150)
        plt.close()
        
        logger.info(f"銘柄別パフォーマンスを出力: {output_path}")
        return output_path
    
    def plot_exit_reason_breakdown(self, trades_df: pd.DataFrame) -> Optional[Path]:
        """
        決済理由の内訳を円グラフでプロット
        
        Args:
            trades_df: トレード結果のDataFrame
            
        Returns:
            出力ファイルパス
        """
        if 'exit_reason' not in trades_df.columns or len(trades_df) == 0:
            logger.warning("決済理由内訳のプロットをスキップ: exit_reasonカラムなしまたはデータなし")
            return None
        
        # 決済理由別に集計
        exit_counts = trades_df['exit_reason'].value_counts()
        
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # 円グラフ
        wedges, texts, autotexts = ax.pie(
            exit_counts.values,
            labels=exit_counts.index,
            autopct='%1.1f%%',
            startangle=90,
            colors=plt.cm.Set3.colors
        )
        
        # テキストのスタイル調整
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)
        
        ax.set_title('決済理由の内訳')
        
        plt.tight_layout()
        
        output_path = self.output_dir / "exit_reason_breakdown.png"
        plt.savefig(output_path, dpi=150)
        plt.close()
        
        logger.info(f"決済理由内訳を出力: {output_path}")
        return output_path
    
    def plot_hold_time_distribution(self, trades_df: pd.DataFrame) -> Optional[Path]:
        """
        保有時間分布のヒストグラムをプロット
        
        Args:
            trades_df: トレード結果のDataFrame
            
        Returns:
            出力ファイルパス
        """
        if 'hold_bars' not in trades_df.columns or len(trades_df) == 0:
            logger.warning("保有時間分布のプロットをスキップ: hold_barsカラムなしまたはデータなし")
            return None
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.hist(trades_df['hold_bars'], bins=30, color='lightcoral',
                edgecolor='darkred', alpha=0.7)
        
        mean_hold = trades_df['hold_bars'].mean()
        ax.axvline(mean_hold, color='blue', linestyle='--', linewidth=2,
                   label=f'平均: {mean_hold:.1f} bars', alpha=0.7)
        
        ax.set_xlabel('保有時間 (bars)')
        ax.set_ylabel('トレード件数')
        ax.set_title('保有時間分布')
        ax.legend()
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        
        output_path = self.output_dir / "hold_time_distribution.png"
        plt.savefig(output_path, dpi=150)
        plt.close()
        
        logger.info(f"保有時間分布を出力: {output_path}")
        return output_path
    
    def plot_all(self, trades_df: pd.DataFrame) -> Dict[str, Path]:
        """
        全てのグラフを一括生成
        
        Args:
            trades_df: トレード結果のDataFrame
            
        Returns:
            出力ファイルパスの辞書
        """
        output_files = {}
        
        # PnL曲線
        pnl_curve_path = self.plot_pnl_curve(trades_df)
        if pnl_curve_path:
            output_files['pnl_curve'] = pnl_curve_path
        
        # PnL分布
        pnl_dist_path = self.plot_pnl_distribution(trades_df)
        if pnl_dist_path:
            output_files['pnl_distribution'] = pnl_dist_path
        
        # 銘柄別パフォーマンス
        symbol_perf_path = self.plot_symbol_performance(trades_df)
        if symbol_perf_path:
            output_files['symbol_performance'] = symbol_perf_path
        
        # 決済理由内訳
        exit_reason_path = self.plot_exit_reason_breakdown(trades_df)
        if exit_reason_path:
            output_files['exit_reason_breakdown'] = exit_reason_path
        
        # 保有時間分布
        hold_time_path = self.plot_hold_time_distribution(trades_df)
        if hold_time_path:
            output_files['hold_time_distribution'] = hold_time_path
        
        logger.info(f"全ての可視化を完了: {self.output_dir}")
        return output_files


# テストハーネス
if __name__ == "__main__":
    import sys
    from datetime import datetime, timedelta
    
    # パス設定
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    print("\n=== Visualizer テスト ===\n")
    
    # テスト用出力ディレクトリ
    test_output_dir = Path("output") / "test_visualizer"
    visualizer = Visualizer(test_output_dir)
    
    # テストデータ生成
    base_time = datetime(2026, 1, 20, 9, 0)
    test_trades = pd.DataFrame({
        'entry_ts': [base_time + timedelta(minutes=i*30) for i in range(20)],
        'exit_ts': [base_time + timedelta(minutes=i*30+15) for i in range(20)],
        'symbol': ['215A', '3350', '5016', '6315'] * 5,
        'direction': ['buy', 'sell'] * 10,
        'entry_price': [1350.0 + i for i in range(20)],
        'exit_price': [1350.0 + i + (5 if i % 3 == 0 else -2) for i in range(20)],
        'pnl_tick': [5.0 if i % 3 == 0 else -2.0 for i in range(20)],
        'hold_bars': [15 + i for i in range(20)],
        'exit_reason': ['TP' if i % 3 == 0 else 'SL' if i % 3 == 1 else 'TO' for i in range(20)],
        'level': [1340.0] * 20
    })
    
    # 全グラフを生成
    output_files = visualizer.plot_all(test_trades)
    
    print("\n=== 出力ファイル ===")
    for name, path in output_files.items():
        print(f"  {name}: {path}")
    
    print("\n✓ Visualizer テスト完了")
