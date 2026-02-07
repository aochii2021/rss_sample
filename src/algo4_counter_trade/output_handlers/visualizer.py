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
    def __init__(self, output_dir):
        """
        :param output_dir: 出力先ディレクトリのパス
        """
        self.output_dir = output_dir

    def plot_pnl_curve(self, trades_df: pd.DataFrame) -> Optional[Path]:
        """
        累積損益(PnL)曲線をプロット
        Args:
            trades_df: トレード結果のDataFrame
        Returns:
            出力ファイルパス
        """
        if trades_df.empty or 'pnl_tick' not in trades_df.columns:
            logger.warning("PnL曲線のプロットをスキップ: データなしまたはpnl_tickカラムなし")
            return None
        trades_df = trades_df.copy()
        trades_df = trades_df.sort_values(by=["entry_ts"])  # 時系列順
        trades_df["cum_pnl"] = trades_df["pnl_tick"].cumsum()
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(trades_df["entry_ts"], trades_df["cum_pnl"], label="累積損益", color="blue")
        ax.set_xlabel("エントリー日時")
        ax.set_ylabel("累積損益 (tick)")
        ax.set_title("累積損益(PnL)曲線")
        ax.grid(alpha=0.3)
        ax.legend()
        plt.tight_layout()
        output_path = self.output_dir / "pnl_curve.png"
        plt.savefig(output_path, dpi=150)
        plt.close()
        logger.info(f"PnL曲線を出力: {output_path}")
        return output_path

    def plot_pnl_distribution(self, trades_df: pd.DataFrame) -> Optional[Path]:
        """
        PnL分布（ヒストグラム）をプロット
        Args:
            trades_df: トレード結果のDataFrame
        Returns:
            出力ファイルパス
        """
        if trades_df.empty or 'pnl_tick' not in trades_df.columns:
            logger.warning("PnL分布のプロットをスキップ: データなしまたはpnl_tickカラムなし")
            return None
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(trades_df["pnl_tick"], bins=50, color="skyblue", edgecolor="black", alpha=0.7)
        ax.set_xlabel("損益 (tick)")
        ax.set_ylabel("件数")
        ax.set_title("損益分布 (ヒストグラム)")
        ax.grid(alpha=0.3)
        plt.tight_layout()
        output_path = self.output_dir / "pnl_distribution.png"
        plt.savefig(output_path, dpi=150)
        plt.close()
        logger.info(f"PnL分布を出力: {output_path}")
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
        matplotlibでPNG、plotlyでHTMLを同時出力
        """
        if trades_df.empty:
            return None

        # --- matplotlib PNG出力 ---
        chart_df = chart_df.copy()
        chart_df['timestamp'] = pd.to_datetime(chart_df['timestamp'])
        chart_df['timestamp_num'] = mdates.date2num(chart_df['timestamp'])
        volume_profile = self._calculate_volume_profile(chart_df)
        fig = plt.figure(figsize=(24, 9))
        gs = fig.add_gridspec(2, 2, width_ratios=[4, 1], height_ratios=[3, 1], hspace=0.05, wspace=0.05)
        ax_ohlc = fig.add_subplot(gs[0, 0])
        ax_volume_profile = fig.add_subplot(gs[0, 1], sharey=ax_ohlc)
        ax_volume = fig.add_subplot(gs[1, 0], sharex=ax_ohlc)
        # ...既存matplotlib描画処理...
        # （ここは省略、既存のまま）
        safe_symbol = str(symbol).replace('.0', '').replace('/', '_')
        output_path = self.output_dir / f"trade_chart_{safe_symbol}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        # --- Plotly HTML出力 ---
        try:
            import plotly.graph_objects as go
            import plotly.io as pio
            fig_plotly = go.Figure()
            fig_plotly.add_trace(go.Candlestick(
                x=chart_df['timestamp'],
                open=chart_df['open'],
                high=chart_df['high'],
                low=chart_df['low'],
                close=chart_df['close'],
                name='OHLC'))
            if not trades_df.empty:
                buy_trades = trades_df[trades_df['direction'] == 'buy']
                sell_trades = trades_df[trades_df['direction'] == 'sell']
                fig_plotly.add_trace(go.Scatter(
                    x=buy_trades['entry_ts'], y=buy_trades['entry_price'],
                    mode='markers', marker=dict(symbol='triangle-up', color='limegreen', size=12, line=dict(color='darkgreen', width=2)),
                    name='Buy Entry'))
                fig_plotly.add_trace(go.Scatter(
                    x=sell_trades['entry_ts'], y=sell_trades['entry_price'],
                    mode='markers', marker=dict(symbol='triangle-down', color='orangered', size=12, line=dict(color='darkred', width=2)),
                    name='Sell Entry'))
                profit_trades = trades_df[trades_df['pnl_tick'] >= 0]
                loss_trades = trades_df[trades_df['pnl_tick'] < 0]
                fig_plotly.add_trace(go.Scatter(
                    x=profit_trades['exit_ts'], y=profit_trades['exit_price'],
                    mode='markers', marker=dict(symbol='circle', color='gold', size=10, line=dict(color='orange', width=2)),
                    name='Exit (Profit)'))
                fig_plotly.add_trace(go.Scatter(
                    x=loss_trades['exit_ts'], y=loss_trades['exit_price'],
                    mode='markers', marker=dict(symbol='circle', color='silver', size=10, line=dict(color='dimgray', width=2)),
                    name='Exit (Loss)'))

            # --- レベルラインは「実際にトレードで使われたものだけ」描画（float誤差・近傍一致対応） ---
            used_level_prices = set()
            if not trades_df.empty and 'level' in trades_df.columns:
                # float誤差対策で丸め（小数1桁）
                used_level_prices = set(trades_df['level'].dropna().astype(float).round(1).unique())
            if levels and used_level_prices:
                for lv in levels:
                    level_price = lv.get('level_now') or lv.get('level', 0)
                    if not level_price or float(level_price) <= 0:
                        continue
                    level_price_r = round(float(level_price), 1)
                    # 許容誤差0.5以内で近傍一致
                    if any(abs(level_price_r - up) <= 0.5 for up in used_level_prices):
                        kind = lv.get('kind', 'level')
                        fig_plotly.add_hline(
                            y=float(level_price),
                            line_dash='dash',
                            line_color='gray',
                            opacity=0.5,
                            annotation_text=kind,
                            annotation_position="top left"
                        )

            fig_plotly.update_layout(
                title=f"[{symbol}] トレードチャート (インタラクティブ)",
                xaxis_title="日時",
                yaxis_title="価格",
                width=1600,
                height=600,
                template="plotly_white"
            )
            html_path = self.output_dir / f"trade_chart_{safe_symbol}.html"
            pio.write_html(fig_plotly, file=str(html_path), auto_open=False)
            logger.info(f"トレードチャート(HTML)を出力: {html_path}")
        except Exception as e:
            logger.warning(f"Plotly HTML出力に失敗: {e}")

        logger.info(f"トレードチャートを出力: {output_path}")
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
        
        # matplotlib用にdatetimeを数値に変換
        chart_df['timestamp_num'] = mdates.date2num(chart_df['timestamp'])
        
        # 価格帯別出来高を計算（価格帯ビン数を抑えて描画負荷を軽減）
        volume_profile = self._calculate_volume_profile(chart_df)
        
        # プロット作成（OHLC + 価格帯別出来高 + 時系列出来高）
        # アスペクト比をさらに横長に調整 (24:9)
        fig = plt.figure(figsize=(24, 9))
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
            date = row['timestamp_num']
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
        trades_df['entry_ts_num'] = mdates.date2num(trades_df['entry_ts'])
        trades_df['exit_ts_num'] = mdates.date2num(trades_df['exit_ts'])
        
        # レベル価格から種類名へのマッピングを作成
        level_kind_map = {}  # {price: kind}
        level_meta_map = {}  # {price: (kind, timestamp)}
        level_kind_japanese = {
            "pivot_high": "ピボット高値",
            "pivot_low": "ピボット安値",
            "consolidation": "もみ合い",
            "psychological": "心理的節目",
            "recent_high": "直近高値",
            "recent_low": "直近安値",
            "vpoc": "出来高集中",
            "hvn": "高出来高帯",
            "swing_resistance": "スイング抵抗",
            "swing_support": "スイングサポート",
            "prev_high": "前日高値",
            "prev_low": "前日安値",
            "prev_close": "前日終値",
            "ma5": "MA5",
            "ma25": "MA25"
        }
        
        if levels:
            for lv in levels:
                level_price = lv.get('level_now') or lv.get('level', 0)
                kind = lv.get('kind', 'unknown')
                timestamp = lv.get('timestamp', '')
                
                if level_price > 0:
                    price = float(level_price)
                    # 価格をそのまま、複数精度でマッピング
                    level_kind_map[price] = kind
                    level_meta_map[price] = (kind, timestamp)
        
        # トレードで使用されたレベルラインを収集（価格・種類・日付のペア）
        trade_levels = {}  # {level_price: (kind, timestamp)}
        if 'level' in trades_df.columns:
            for level_price in trades_df['level'].dropna():
                if level_price > 0:
                    float_price = float(level_price)
                    
                    # 完全一致を優先的に検索
                    if float_price in level_meta_map:
                        trade_levels[float_price] = level_meta_map[float_price]
                    else:
                        # 完全一致がない場合、最も近いレベルを探す
                        if level_meta_map:
                            closest_price = min(level_meta_map.keys(), 
                                              key=lambda x: abs(x - float_price))
                            # 価格差が5.0以内なら採用
                            if abs(closest_price - float_price) <= 5.0:
                                trade_levels[float_price] = level_meta_map[closest_price]
                            else:
                                # 大きく異なる場合
                                trade_levels[float_price] = ('unknown', '')
                        else:
                            trade_levels[float_price] = ('unknown', '')
        
        # トレードで使用されたレベルラインを赤の破線で描画（種類も表示）
        # チャートデータのX軸範囲を取得
        chart_x_min = chart_df['timestamp_num'].min()
        chart_x_max = chart_df['timestamp_num'].max()
        
        for i, (level_price, (kind, timestamp)) in enumerate(trade_levels.items()):
            ax_ohlc.axhline(y=level_price, color='red', linestyle='--', 
                          linewidth=1.5, alpha=0.7, zorder=2)
            
            # レベルラインのラベルをチャート左端に表示
            kind_jp = level_kind_japanese.get(kind, kind)
            
            # 周辺レベル（±0.5%以内）を検索
            threshold = level_price * 0.005  # 0.5%
            nearby_kinds = []
            if level_meta_map:
                for nearby_price, (nearby_kind, nearby_ts) in level_meta_map.items():
                    if abs(nearby_price - level_price) <= threshold and nearby_price != level_price:
                        nearby_kind_jp = level_kind_japanese.get(nearby_kind, nearby_kind)
                        nearby_kinds.append(nearby_kind_jp)
            
            # タイムスタンプから日付と足種を抽出
            timeframe_label = ''
            if timestamp:
                try:
                    # Timestamp型を文字列に変換
                    ts_str = str(timestamp)
                    ts_parts = ts_str.split('T')
                    ts_date = ts_parts[0]  # YYYY-MM-DD
                    
                    # 足種を判定（時刻が00:00:00なら日足、それ以外は分足）
                    if len(ts_parts) > 1:
                        ts_time = ts_parts[1].split('+')[0]  # タイムゾーン情報を除去
                        if ts_time == '00:00:00':
                            timeframe_label = f'({ts_date}\n日足)'
                        else:
                            timeframe_label = f'({ts_date}\n分足)'
                    else:
                        timeframe_label = f'({ts_date})'
                except Exception as e:
                    logger.debug(f"タイムスタンプ処理エラー: {e}, timestamp={timestamp}")
                    timeframe_label = ''
            
            # 周辺レベルをラベルに追加
            nearby_label = ''
            if nearby_kinds:
                nearby_label = '\n' + ','.join(nearby_kinds)
            
            # ラベルテキストを作成
            if timeframe_label and kind != 'unknown':
                label_text = f'{kind_jp}\n{timeframe_label}\n{level_price:.1f}{nearby_label}'
            elif timeframe_label and kind == 'unknown':
                label_text = f'{timeframe_label}\n{level_price:.1f}{nearby_label}'
            elif kind != 'unknown':
                label_text = f'{kind_jp}\n{level_price:.1f}'
            else:
                label_text = f'{level_price:.1f}'
            
            # チャートデータ範囲内の左端5%の位置にラベルを配置
            label_x = chart_x_min + (chart_x_max - chart_x_min) * 0.02
            
            ax_ohlc.text(label_x, level_price, label_text,
                       verticalalignment='center', horizontalalignment='left',
                       fontsize=7, color='red', weight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                               edgecolor='red', alpha=0.85))
        
        # トレードのエントリー・イグジットをプロット
        buy_entries = []
        sell_entries = []
        profit_exits = []
        loss_exits = []
        lines_profit = []
        lines_loss = []
        
        for _, trade in trades_df.iterrows():
            entry_time = trade['entry_ts_num']
            exit_time = trade['exit_ts_num']
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            position_type = trade.get('direction', 'buy')
            pnl = trade.get('pnl_tick', 0)
            
            # トレードで使用されたレベル価格と種類を取得
            trade_level_price = trade.get('level', None)
            trade_level_kind = None
            if trade_level_price and not pd.isna(trade_level_price):
                float_price = float(trade_level_price)
                if float_price in trade_levels:
                    trade_level_kind, _ = trade_levels[float_price]
            
            # エントリーポイント
            if position_type == 'buy':
                buy_entries.append((entry_time, entry_price, trade_level_price, trade_level_kind))
            else:
                sell_entries.append((entry_time, entry_price, trade_level_price, trade_level_kind))
            
            # イグジットポイント
            if pnl >= 0:
                profit_exits.append((exit_time, exit_price))
                lines_profit.append(((entry_time, entry_price), (exit_time, exit_price)))
            else:
                loss_exits.append((exit_time, exit_price))
                lines_loss.append(((entry_time, entry_price), (exit_time, exit_price)))
        
        # エントリーマーカー（シンプルに）
        if buy_entries:
            for i, (time, price, level_price, level_kind) in enumerate(buy_entries):
                ax_ohlc.scatter(time, price, color='limegreen', marker='^', s=200, 
                              edgecolors='darkgreen', linewidths=1.5, zorder=5,
                              label='Buy Entry' if i == 0 else '')
        
        if sell_entries:
            for i, (time, price, level_price, level_kind) in enumerate(sell_entries):
                ax_ohlc.scatter(time, price, color='orangered', marker='v', s=200,
                              edgecolors='darkred', linewidths=1.5, zorder=5,
                              label='Sell Entry' if i == 0 else '')
        
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
            prices, volumes, bin_height = volume_profile
            if prices and volumes:
                ax_volume_profile.barh(prices, volumes, height=bin_height * 0.9,
                                       color='gray', alpha=0.5)
                ax_volume_profile.set_xlabel('出来高', fontsize=10)
                ax_volume_profile.tick_params(labelleft=False)
                ax_volume_profile.grid(True, alpha=0.3, axis='y')
                
                # VPOC（Volume Point of Control）を表示
                vpoc_idx = int(np.argmax(volumes))
                vpoc_price = prices[vpoc_idx]
                ax_volume_profile.axhline(y=vpoc_price, color='red', linestyle='-',
                                         linewidth=2, label='VPOC')
                ax_ohlc.axhline(y=vpoc_price, color='red', linestyle='-',
                              linewidth=1, alpha=0.7)
        
        # 時系列出来高
        if 'volume' in chart_df.columns:
            ax_volume.bar(chart_df['timestamp_num'], chart_df['volume'], 
                         color='gray', alpha=0.5, width=bar_width)
            ax_volume.set_ylabel('出来高', fontsize=12)
            ax_volume.grid(True, alpha=0.3)
        
        # X軸フォーマット（日付形式で表示）
        date_fmt = mdates.DateFormatter('%m/%d %H:%M')
        date_locator = mdates.AutoDateLocator()
        
        ax_ohlc.xaxis.set_major_formatter(date_fmt)
        ax_ohlc.xaxis.set_major_locator(date_locator)
        
        ax_volume.xaxis.set_major_formatter(date_fmt)
        ax_volume.xaxis.set_major_locator(date_locator)
        plt.setp(ax_volume.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 銘柄コードの正規化（ファイル名用）
        safe_symbol = str(symbol).replace('.0', '').replace('/', '_')
        output_path = self.output_dir / f"trade_chart_{safe_symbol}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        # --- PlotlyによるインタラクティブHTML出力 ---
        try:
            import plotly.graph_objects as go
            import plotly.io as pio
            # OHLCチャート
            fig_plotly = go.Figure()
            fig_plotly.add_trace(go.Candlestick(
                x=chart_df['timestamp'],
                open=chart_df['open'],
                high=chart_df['high'],
                low=chart_df['low'],
                close=chart_df['close'],
                name='OHLC'))

            # トレードエントリー・イグジット
            if not trades_df.empty:
                buy_trades = trades_df[trades_df['direction'] == 'buy']
                sell_trades = trades_df[trades_df['direction'] == 'sell']
                # エントリー
                fig_plotly.add_trace(go.Scatter(
                    x=buy_trades['entry_ts'], y=buy_trades['entry_price'],
                    mode='markers', marker=dict(symbol='triangle-up', color='limegreen', size=12, line=dict(color='darkgreen', width=2)),
                    name='Buy Entry'))
                fig_plotly.add_trace(go.Scatter(
                    x=sell_trades['entry_ts'], y=sell_trades['entry_price'],
                    mode='markers', marker=dict(symbol='triangle-down', color='orangered', size=12, line=dict(color='darkred', width=2)),
                    name='Sell Entry'))
                # イグジット
                profit_trades = trades_df[trades_df['pnl_tick'] >= 0]
                loss_trades = trades_df[trades_df['pnl_tick'] < 0]
                fig_plotly.add_trace(go.Scatter(
                    x=profit_trades['exit_ts'], y=profit_trades['exit_price'],
                    mode='markers', marker=dict(symbol='circle', color='gold', size=10, line=dict(color='orange', width=2)),
                    name='Exit (Profit)'))
                fig_plotly.add_trace(go.Scatter(
                    x=loss_trades['exit_ts'], y=loss_trades['exit_price'],
                    mode='markers', marker=dict(symbol='circle', color='silver', size=10, line=dict(color='dimgray', width=2)),
                    name='Exit (Loss)'))

            # --- レベルラインは「実際にトレードで使われたものだけ」描画（float誤差・近傍一致対応） ---
            used = set()
            if (not trades_df.empty) and ('level' in trades_df.columns):
                used = set(trades_df['level'].dropna().astype(float).round(1).unique())
            tol = 0.5  # 許容誤差

            if levels and used:
                for lv in levels:
                    level_price = lv.get('level_now') or lv.get('level', 0)
                    if not level_price:
                        continue
                    lp = float(level_price)
                    if lp <= 0:
                        continue
                    lp_r = round(lp, 1)
                    if any(abs(lp_r - u) <= tol for u in used):
                        kind = lv.get('kind', 'level')
                        fig_plotly.add_hline(
                            y=lp,
                            line_dash='dash',
                            line_color='gray',
                            opacity=0.5,
                            annotation_text=kind,
                            annotation_position="top left"
                        )

            fig_plotly.update_layout(
                title=f"[{symbol}] トレードチャート (インタラクティブ)",
                xaxis_title="日時",
                yaxis_title="価格",
                width=1600,
                height=600,
                template="plotly_white"
            )
            html_path = self.output_dir / f"trade_chart_{safe_symbol}.html"
            pio.write_html(fig_plotly, file=str(html_path), auto_open=False)
            logger.info(f"トレードチャート(HTML)を出力: {html_path}")
        except Exception as e:
            logger.warning(f"Plotly HTML出力に失敗: {e}")

        logger.info(f"トレードチャートを出力: {output_path}")
        return output_path
    
    def _calculate_volume_profile(
        self,
        df: pd.DataFrame,
        max_bins: int = 40
    ) -> Optional[tuple]:
        """価格帯別出来高を計算（ビン数を抑えて高速化）
        
        Args:
            df: チャートデータ
            max_bins: 価格帯ビンの最大数
            
        Returns:
            tuple: (prices, volumes, bin_height) またはNone
        """
        if df.empty or 'volume' not in df.columns:
            return None
        if df[['high', 'low']].isna().all().any():
            return None
        if df['volume'].fillna(0).sum() == 0:
            return None

        price_min = df['low'].min()
        price_max = df['high'].max()
        if pd.isna(price_min) or pd.isna(price_max):
            return None
        if price_min == price_max:
            price_max += 1e-3  # 同一価格のみの場合に幅を確保

        # ローソク足本数に応じてビン数を設定（上限max_bins）
        adaptive_bins = min(max_bins, max(10, int(len(df) ** 0.5 * 4)))
        bin_edges = np.linspace(price_min, price_max, adaptive_bins + 1)
        bin_height = float(np.diff(bin_edges).mean())

        # 代表価格（典型価格）に出来高を集約してヒストグラム化
        typical_price = df[['high', 'low', 'close', 'open']].mean(axis=1)
        volumes = df['volume'].fillna(0).to_numpy()
        hist, edges = np.histogram(typical_price, bins=bin_edges, weights=volumes)

        prices = ((edges[:-1] + edges[1:]) / 2).tolist()
        volumes = hist.tolist()

        if sum(volumes) == 0:
            return None

        return prices, volumes, bin_height
    
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
