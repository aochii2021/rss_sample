#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
過去N営業日分足揉み合いゾーンの可視化
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import json
from datetime import datetime
import os
import glob
import numpy as np

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False

def visualize_consolidation_zones(trade_date_str, lookback_days=5):
    """
    指定日の揉み合いゾーンとトレードを可視化
    
    Args:
        trade_date_str: 取引日（'20260119'形式）
        lookback_days: 過去何営業日のデータを使用するか
    """
    date_formatted = f"{trade_date_str[:4]}-{trade_date_str[4:6]}-{trade_date_str[6:]}"
    
    # レベルデータを読み込み
    levels_path = f"output/levels_intraday5d_{trade_date_str}.jsonl"
    if not os.path.exists(levels_path):
        print(f"レベルファイルが見つかりません: {levels_path}")
        return
    
    levels = []
    with open(levels_path, 'r', encoding='utf-8') as f:
        for line in f:
            levels.append(json.loads(line))
    
    # トレードデータを読み込み
    trades_path = f"output/trades_5d_{trade_date_str}.csv"
    if not os.path.exists(trades_path):
        print(f"トレードファイルが見つかりません: {trades_path}")
        return
    
    df_trades = pd.read_csv(trades_path)
    df_trades['entry_ts'] = pd.to_datetime(df_trades['entry_ts'])
    df_trades['exit_ts'] = pd.to_datetime(df_trades['exit_ts'])
    
    # LOBデータを読み込み（価格データ）
    lob_path = f"output/lob_features_5d_{trade_date_str}.csv"
    df_lob = pd.read_csv(lob_path)
    df_lob['ts'] = pd.to_datetime(df_lob['ts'])
    
    # 銘柄別に処理
    symbols = df_lob['symbol'].unique()
    print(f"  対象銘柄: {len(symbols)}件")
    
    for symbol in symbols:
        if pd.isna(symbol):
            continue
        
        print(f"  処理中: {symbol}...", end=" ")
        
        # 銘柄のレベルを抽出
        symbol_levels = [lv for lv in levels if lv.get('symbol') == str(symbol)]
        if not symbol_levels:
            print("レベルなし")
            continue
        
        # 分足揉み合いゾーンと日足補完を分離
        intraday_zones = [lv for lv in symbol_levels if lv.get('type', '').startswith('intraday_consolidation')]
        daily_zones = [lv for lv in symbol_levels if lv.get('metadata', {}).get('source') == 'daily_fallback']
        
        # 銘柄のLOBデータとトレードを抽出
        df_sym = df_lob[df_lob['symbol'] == symbol].copy()
        df_trades_sym = df_trades[df_trades['symbol'] == symbol].copy()
        
        if df_sym.empty:
            continue
        
        # 過去N営業日の分足データから価格帯別出来高を計算
        symbol_str = str(symbol)
        if '.' in symbol_str:
            sym_code = symbol_str.split('.')[0]
        else:
            sym_code = symbol_str
        
        # 分足データを読み込み
        chart_pattern = f"input/chart_data/stock_chart_3M_{sym_code}_*.csv"
        chart_files = glob.glob(chart_pattern)
        
        volume_profile = None
        if chart_files:
            df_chart = pd.read_csv(chart_files[0], encoding='utf-8-sig')
            if '日付' in df_chart.columns and '出来高' in df_chart.columns and '終値' in df_chart.columns:
                df_chart['日付'] = pd.to_datetime(df_chart['日付'])
                
                # 過去指定営業日のデータを抽出（レベル生成と同じロジック）
                all_dates = sorted(df_chart['日付'].dt.date.unique())
                trade_date = datetime.strptime(trade_date_str, '%Y%m%d').date()
                past_dates = [d for d in all_dates if d < trade_date]
                
                if len(past_dates) >= lookback_days:
                    target_dates = past_dates[-lookback_days:]
                    df_chart_filtered = df_chart[df_chart['日付'].dt.date.isin(target_dates)].copy()
                    
                    # NaNを除外
                    df_chart_filtered = df_chart_filtered[df_chart_filtered['終値'].notna()].copy()
                    
                    if len(df_chart_filtered) > 0:
                        # 価格帯別に出来高を集計
                        prices = df_chart_filtered['終値'].values
                        volumes = df_chart_filtered['出来高'].values
                        
                        if len(prices) > 0 and len(volumes) > 0:
                            price_min, price_max = float(prices.min()), float(prices.max())
                            
                            # 価格範囲が有効な場合のみビンを作成
                            if price_max > price_min:
                                bin_size = max(0.5, (price_max - price_min) / 100)  # 最低0.5円、最大100ビン
                                bins = np.arange(price_min - bin_size, price_max + bin_size * 2, bin_size)
                                
                                # ヒストグラムで集計
                                hist, bin_edges = np.histogram(prices, bins=bins, weights=volumes)
                                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                                
                                volume_profile = pd.DataFrame({
                                    'price': bin_centers,
                                    'volume': hist
                                })
        
        # プロット作成（2列：メインチャート + 出来高プロファイル）
        fig = plt.figure(figsize=(18, 10))
        gs = gridspec.GridSpec(1, 2, width_ratios=[4, 1], wspace=0.05)
        ax = fig.add_subplot(gs[0])
        ax_vol = fig.add_subplot(gs[1], sharey=ax)
        
        # 価格推移（mid price）
        ax.plot(df_sym['ts'], df_sym['mid'], label='Mid Price', color='black', linewidth=0.8, alpha=0.7)
        
        # 日別の色を定義（3営業日分）
        colors = {
            '2026-01-14': 'lightblue',
            '2026-01-15': 'lightgreen',
            '2026-01-16': 'lightyellow'
        }
        
        # 分足揉み合いゾーンを描画
        for i, zone in enumerate(intraday_zones):
            metadata = zone.get('metadata', {})
            zone_start = metadata.get('zone_start')
            zone_end = metadata.get('zone_end')
            date = metadata.get('date', '')
            strength = zone.get('strength', 0)
            
            if zone_start is None or zone_end is None:
                continue
            
            # 日付に応じた色
            color = colors.get(str(date), 'lightgray')
            
            # 横線（ゾーン）
            ax.axhspan(zone_start, zone_end, alpha=0.3, color=color, 
                      label=f'分足揉み合い {date}' if i == 0 else '')
            
            # 中心線
            ax.axhline(y=zone['level_now'], color=color, linestyle='--', 
                      linewidth=1.5, alpha=0.7)
            
            # ラベル
            ax.text(df_sym['ts'].iloc[0], zone['level_now'], 
                   f" {date} (強度:{strength:.2f})", 
                   fontsize=8, verticalalignment='center',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.5))
        
        # 日足補完ゾーンを描画
        for i, zone in enumerate(daily_zones):
            metadata = zone.get('metadata', {})
            zone_start = metadata.get('zone_start')
            zone_end = metadata.get('zone_end')
            
            if zone_start is None or zone_end is None:
                continue
            
            # 日足は薄い赤で表示
            ax.axhspan(zone_start, zone_end, alpha=0.15, color='red', 
                      label='日足補完' if i == 0 else '')
            ax.axhline(y=zone['level_now'], color='red', linestyle=':', 
                      linewidth=1, alpha=0.5)
        
        # トレードのエントリー・エグジットを描画
        for _, trade in df_trades_sym.iterrows():
            # エントリーポイント
            if trade['direction'] == 'buy':
                ax.scatter(trade['entry_ts'], trade['entry_price'], 
                          color='blue', marker='^', s=100, zorder=5, label='買いエントリー')
            else:
                ax.scatter(trade['entry_ts'], trade['entry_price'], 
                          color='red', marker='v', s=100, zorder=5, label='売りエントリー')
            
            # エグジットポイント
            exit_color = 'green' if trade['pnl_tick'] > 0 else 'darkred'
            ax.scatter(trade['exit_ts'], trade['exit_price'], 
                      color=exit_color, marker='x', s=100, zorder=5)
            
            # エントリー→エグジットの線
            ax.plot([trade['entry_ts'], trade['exit_ts']], 
                   [trade['entry_price'], trade['exit_price']], 
                   color=exit_color, linestyle='-', linewidth=1.5, alpha=0.5)
            
            # P&L表示
            ax.text(trade['exit_ts'], trade['exit_price'], 
                   f" {trade['pnl_tick']:+.1f}t ({trade['exit_reason']})", 
                   fontsize=8, color=exit_color,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        # 軸設定
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.tick_params(axis='x', rotation=45)
        
        ax.set_xlabel('時刻', fontsize=12)
        ax.set_ylabel('価格', fontsize=12)
        ax.set_title(f'{symbol} - 過去{lookback_days}営業日分足揉み合いゾーン ({date_formatted})', fontsize=14, fontweight='bold')
        
        # 凡例（重複を削除）
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='best', fontsize=9)
        
        ax.grid(True, alpha=0.3)
        
        # 出来高プロファイルを描画
        if volume_profile is not None and not volume_profile.empty:
            ax_vol.barh(volume_profile['price'], volume_profile['volume'], 
                       height=0.4, color='steelblue', alpha=0.6)
            ax_vol.set_xlabel('出来高', fontsize=10)
            ax_vol.set_title(f'価格帯別出来高\n(過去{lookback_days}営業日)', fontsize=10)
            ax_vol.grid(True, alpha=0.3, axis='x')
            ax_vol.tick_params(axis='y', labelleft=False)  # y軸ラベルは左側と共有
            
            # 出来高の多い価格帯をハイライト
            if len(volume_profile) > 0:
                max_vol_idx = volume_profile['volume'].idxmax()
                max_vol_price = volume_profile.loc[max_vol_idx, 'price']
                ax_vol.axhline(y=max_vol_price, color='red', linestyle='--', 
                             linewidth=2, alpha=0.7, label='最大出来高価格')
                ax_vol.legend(fontsize=8)
        else:
            ax_vol.text(0.5, 0.5, 'データなし', ha='center', va='center', 
                       transform=ax_vol.transAxes, fontsize=12)
            ax_vol.set_xlabel('出来高', fontsize=10)
            ax_vol.tick_params(axis='y', labelleft=False)
        
        fig.tight_layout()
        
        # 保存
        output_dir = "output/figs"
        os.makedirs(output_dir, exist_ok=True)
        output_path = f"{output_dir}/consolidation_zones_{symbol}_{trade_date_str}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"OK")
        plt.close()

def main():
    # ========== 設定 ==========
    LOOKBACK_DAYS = 3  # 過去何営業日のデータを表示するか
    
    print(f"=== 揉み合いゾーン可視化（過去{LOOKBACK_DAYS}営業日） ===\n")
    
    dates = ['20260119', '20260120']
    
    for date in dates:
        print(f"\n■ {date[:4]}-{date[4:6]}-{date[6:]}")
        visualize_consolidation_zones(date, lookback_days=LOOKBACK_DAYS)
    
    print("\n=== 完了 ===")
    print("保存先: output/figs/consolidation_zones_*.png")

if __name__ == "__main__":
    main()
