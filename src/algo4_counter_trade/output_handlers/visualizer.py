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
import numpy as np
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
    
    def plot_trade_chart(
        self,
        symbol: str,
        chart_df: pd.DataFrame,
        trades_df: pd.DataFrame,
        levels: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Path]:
        """
        トレード箇所を可視化したチャートを生成（ろうそく足 + 価格帯別出来高）
        
        Args:
            symbol: 銘柄コード
            chart_df: 価格チャートデータ（timestamp, open, high, low, close, volume列が必要）
            trades_df: その銘柄のトレードデータ
            levels: S/Rレベルリスト（オプション）
            
        Returns:
            出力ファイルパス
        """
        if trades_df.empty:
            return None
        
        # timestampをdatetimeに変換
        chart_df = chart_df.copy()
        chart_df['timestamp'] = pd.to_datetime(chart_df['timestamp'])
        
        # 価格帯別出来高を計算
        volume_profile = self._calculate_volume_profile(chart_df, bin_size=1.0)
        
        # プロット作成（OHLC + 価格帯別出来高 + 時系列出来高）
        fig = plt.figure(figsize=(18, 10))
        gs = fig.add_gridspec(2, 2, width_ratios=[4, 1], height_ratios=[3, 1], 
                             hspace=0.05, wspace=0.05)
        
        ax_ohlc = fig.add_subplot(gs[0, 0])  # OHLCチャート
        ax_volume_profile = fig.add_subplot(gs[0, 1], sharey=ax_ohlc)  # 価格帯別出来高
        ax_volume = fig.add_subplot(gs[1, 0], sharex=ax_ohlc)  # 時系列出来高
        
        # OHLCキャンドルスティック
        bar_width = 0.6 / 24  # 5分足想定
        if len(chart_df) > 1:
            time_delta = (chart_df['timestamp'].max() - chart_df['timestamp'].min()).total_seconds()
            bar_width = time_delta / len(chart_df) / 86400 * 0.6
        
        for idx, row in chart_df.iterrows():
            date = row['timestamp']
            open_price = row.get('open')
            high = row.get('high')
            low = row.get('low')
            close = row.get('close')
            
            if pd.isna(open_price) or pd.isna(close):
                continue
            
            color = 'red' if close >= open_price else 'blue'
            
            # ローソク足の実体
            ax_ohlc.plot([date, date], [open_price, close], color=color, 
                        linewidth=4, solid_capstyle='butt')
            
            # ヒゲ
            if not pd.isna(high):
                ax_ohlc.plot([date, date], [max(open_price, close), high], 
                           color=color, linewidth=1)
            if not pd.isna(low):
                ax_ohlc.plot([date, date], [min(open_price, close), low], 
                           color=color, linewidth=1)
        
        # S/Rレベル線を描画
        level_colors = {
            "recent_high": "red",
            "recent_low": "green",
            "vpoc": "purple",
            "hvn": "magenta",
            "swing_resistance": "darkred",
            "swing_support": "darkgreen",
            "prev_high": "orange",
            "prev_low": "cyan",
            "prev_close": "gray"
        }
        
        drawn_levels = set()
        level_annotations = {}  # レベル価格 → レベル情報のマッピング
        
        if levels:
            for lv in levels:
                kind = lv.get('kind', 'unknown')
                level_price = lv.get('level', 0)
                strength = lv.get('strength', 0.5)
                
                if level_price <= 0:
                    continue
                
                if level_price in drawn_levels:
                    continue
                drawn_levels.add(level_price)
                level_annotations[level_price] = lv
                
                color = level_colors.get(kind, 'gray')
                alpha = 0.3 + 0.6 * strength
                linewidth = 0.5 + 1.5 * strength
                
                ax_ohlc.axhline(y=level_price, color=color, linestyle='--', 
                              linewidth=linewidth, alpha=alpha, zorder=1)
        
        # トレードデータ準備
        trades_df = trades_df.copy()
        trades_df['entry_ts'] = pd.to_datetime(trades_df['entry_ts'])
        trades_df['exit_ts'] = pd.to_datetime(trades_df['exit_ts'])
        
        # トレードのエントリー・イグジットをプロット
        buy_entries = []
        sell_entries = []
        profit_exits = []
        loss_exits = []
        lines_profit = []
        lines_loss = []
        
        for _, trade in trades_df.iterrows():
            entry_time = trade['entry_ts']
            exit_time = trade['exit_ts']
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            position_type = trade.get('direction', 'buy')
            pnl = trade.get('pnl_tick', 0)
            
            # エントリーに最も近いレベルを特定
            closest_level = self._find_closest_level(entry_price, level_annotations)
            
            # エントリーポイント
            if position_type == 'buy':
                buy_entries.append((entry_time, entry_price, closest_level))
            else:
                sell_entries.append((entry_time, entry_price, closest_level))
            
            # イグジットポイント
            if pnl >= 0:
                profit_exits.append((exit_time, exit_price))
                lines_profit.append(((entry_time, entry_price), (exit_time, exit_price)))
            else:
                loss_exits.append((exit_time, exit_price))
                lines_loss.append(((entry_time, entry_price), (exit_time, exit_price)))
        
        # エントリーマーカーと根拠レベルのアノテーション
        if buy_entries:
            for i, (time, price, level_info) in enumerate(buy_entries):
                ax_ohlc.scatter(time, price, color='limegreen', marker='^', s=200, 
                              edgecolors='darkgreen', linewidths=1.5, zorder=5)
                
                # 根拠レベルをアノテーション（最初の3つのみ、重複を避ける）
                if level_info and i < 3:
                    kind = level_info.get('kind', 'unknown')
                    level_price = level_info.get('level')
                    ax_ohlc.annotate(f'{kind}\n{level_price:.1f}', 
                                   xy=(time, price), xytext=(10, -30),
                                   textcoords='offset points', fontsize=8,
                                   bbox=dict(boxstyle='round,pad=0.3', 
                                           facecolor='limegreen', alpha=0.7),
                                   arrowprops=dict(arrowstyle='->', 
                                                 connectionstyle='arc3,rad=0'))
        
        if sell_entries:
            for i, (time, price, level_info) in enumerate(sell_entries):
                ax_ohlc.scatter(time, price, color='orangered', marker='v', s=200,
                              edgecolors='darkred', linewidths=1.5, zorder=5)
                
                if level_info and i < 3:
                    kind = level_info.get('kind', 'unknown')
                    level_price = level_info.get('level')
                    ax_ohlc.annotate(f'{kind}\n{level_price:.1f}', 
                                   xy=(time, price), xytext=(10, 30),
                                   textcoords='offset points', fontsize=8,
                                   bbox=dict(boxstyle='round,pad=0.3', 
                                           facecolor='orangered', alpha=0.7),
                                   arrowprops=dict(arrowstyle='->', 
                                                 connectionstyle='arc3,rad=0'))
        
        # イグジットマーカー
        if profit_exits:
            times, prices = zip(*profit_exits)
            ax_ohlc.scatter(times, prices, color='gold', marker='o', s=150,
                          edgecolors='orange', linewidths=1.5, label='Exit (Profit)', zorder=5)
        
        if loss_exits:
            times, prices = zip(*loss_exits)
            ax_ohlc.scatter(times, prices, color='silver', marker='o', s=150,
                          edgecolors='dimgray', linewidths=1.5, label='Exit (Loss)', zorder=5)
        
        # エントリー→イグジットの線
        for (entry_time, entry_price), (exit_time, exit_price) in lines_profit:
            ax_ohlc.plot([entry_time, exit_time], [entry_price, exit_price],
                       color='green', linestyle='-', linewidth=1.5, alpha=0.6, zorder=3)
        
        for (entry_time, entry_price), (exit_time, exit_price) in lines_loss:
            ax_ohlc.plot([entry_time, exit_time], [entry_price, exit_price],
                       color='red', linestyle='--', linewidth=1.5, alpha=0.6, zorder=3)
        
        # 軸ラベル（OHLCチャート）
        ax_ohlc.set_ylabel('価格', fontsize=12)
        ax_ohlc.set_title(f'[{symbol}] トレードチャート ({len(trades_df)} trades)', 
                         fontsize=14, fontweight='bold')
        ax_ohlc.grid(True, alpha=0.3)
        ax_ohlc.tick_params(labelbottom=False)
        
        # 凡例（重複除外）
        handles, labels = ax_ohlc.get_legend_handles_labels()
        if handles:
            by_label = dict(zip(labels, handles))
            ax_ohlc.legend(by_label.values(), by_label.keys(), loc='best', fontsize=8)
        
        # 価格帯別出来高を描画
        if volume_profile:
            prices = sorted(volume_profile.keys())
            volumes = [volume_profile[p] for p in prices]
            
            ax_volume_profile.barh(prices, volumes, height=0.8, color='gray', alpha=0.5)
            ax_volume_profile.set_xlabel('出来高', fontsize=10)
            ax_volume_profile.tick_params(labelleft=False)
            ax_volume_profile.grid(True, alpha=0.3, axis='y')
            
            # VPOC（Volume Point of Control）を表示
            vpoc_price = max(volume_profile, key=volume_profile.get)
            ax_volume_profile.axhline(y=vpoc_price, color='red', linestyle='-', 
                                     linewidth=2, label='VPOC')
            ax_ohlc.axhline(y=vpoc_price, color='red', linestyle='-', 
                          linewidth=1, alpha=0.7)
        
        # 時系列出来高
        if 'volume' in chart_df.columns:
            ax_volume.bar(chart_df['timestamp'], chart_df['volume'], 
                         color='gray', alpha=0.5, width=bar_width)
            ax_volume.set_ylabel('出来高', fontsize=12)
            ax_volume.grid(True, alpha=0.3)
        
        # X軸フォーマット
        ax_volume.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        ax_volume.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax_volume.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 銘柄コードの正規化（ファイル名用）
        safe_symbol = str(symbol).replace('.0', '').replace('/', '_')
        output_path = self.output_dir / f"trade_chart_{safe_symbol}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"トレードチャートを出力: {output_path}")
        return output_path
    
    def _calculate_volume_profile(self, df: pd.DataFrame, bin_size: float = 1.0) -> dict:
        """価格帯別出来高を計算
        
        Args:
            df: チャートデータ
            bin_size: 価格帯のビンサイズ
            
        Returns:
            dict: {price: volume}
        """
        volume_profile = {}
        
        for _, row in df.iterrows():
            high = row.get('high')
            low = row.get('low')
            volume = row.get('volume', 0)
            
            if pd.isna(high) or pd.isna(low) or pd.isna(volume) or volume == 0:
                continue
            
            # 高値〜安値の範囲を分割
            min_price = int(low / bin_size) * bin_size
            max_price = int(high / bin_size) * bin_size + bin_size
            
            price_range = np.arange(min_price, max_price, bin_size)
            vol_per_bin = volume / len(price_range) if len(price_range) > 0 else 0
            
            for price in price_range:
                volume_profile[price] = volume_profile.get(price, 0) + vol_per_bin
        
        return volume_profile
    
    def _find_closest_level(self, entry_price: float, level_annotations: dict) -> dict:
        """エントリー価格に最も近いレベルを特定
        
        Args:
            entry_price: エントリー価格
            level_annotations: レベル情報の辞書 {level_price: level_info}
            
        Returns:
            dict: 最も近いレベルの情報
        """
        if not level_annotations:
            return None
        
        closest_level_price = min(level_annotations.keys(), 
                                 key=lambda x: abs(x - entry_price))
        
        # 価格差が大きすぎる場合はNoneを返す（閾値: 5円）
        if abs(closest_level_price - entry_price) > 5.0:
            return None
        
        return level_annotations[closest_level_price]
    
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
