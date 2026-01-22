#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
取得したチャートデータ（日足・3分足）を可視化
価格帯別出来高と揉み合い価格帯を表示
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import glob

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
FIG_DIR = os.path.join(OUTPUT_DIR, 'figs')
os.makedirs(FIG_DIR, exist_ok=True)

def parse_date(date_str):
    """日付文字列をdatetimeに変換"""
    try:
        return pd.to_datetime(date_str, format='%Y/%m/%d')
    except:
        try:
            return pd.to_datetime(date_str)
        except:
            return None

def calculate_volume_profile(df, bin_size=1.0):
    """
    価格帯別出来高を計算
    
    Returns:
        dict: {price: volume}
    """
    volume_profile = {}
    
    for _, row in df.iterrows():
        high = row.get('高値')
        low = row.get('安値')
        volume = row.get('出来高', 0)
        
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

def detect_consolidation_zones(volume_profile, threshold_percentile=70, min_width=3):
    """
    揉み合い価格帯を検出
    
    Args:
        volume_profile: 価格帯別出来高辞書
        threshold_percentile: 出来高の閾値パーセンタイル
        min_width: 最小の連続価格帯数
    
    Returns:
        list: [(start_price, end_price), ...]
    """
    if not volume_profile:
        return []
    
    # 出来高でソート
    sorted_prices = sorted(volume_profile.keys())
    volumes = [volume_profile[p] for p in sorted_prices]
    
    if len(volumes) == 0:
        return []
    
    # 閾値を計算
    threshold = np.percentile(volumes, threshold_percentile)
    
    # 連続する高出来高価格帯を検出
    zones = []
    zone_start = None
    
    for i, price in enumerate(sorted_prices):
        vol = volume_profile[price]
        
        if vol >= threshold:
            if zone_start is None:
                zone_start = price
        else:
            if zone_start is not None:
                zone_end = sorted_prices[i-1]
                if (i - sorted_prices.index(zone_start)) >= min_width:
                    zones.append((zone_start, zone_end))
                zone_start = None
    
    # 最後の区間処理
    if zone_start is not None:
        zone_end = sorted_prices[-1]
        if (len(sorted_prices) - sorted_prices.index(zone_start)) >= min_width:
            zones.append((zone_start, zone_end))
    
    return zones

def visualize_ohlc(csv_path, symbol, timeframe):
    """OHLCチャート可視化（価格帯別出来高と揉み合い価格帯付き）"""
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    
    # 日付列を変換
    if '日付' in df.columns:
        if '時刻' in df.columns:
            # 時刻列がある場合（分足データ）
            df['date'] = pd.to_datetime(df['日付'] + ' ' + df['時刻'], format='%Y/%m/%d %H:%M', errors='coerce')
            df['date_only'] = df['date'].dt.date  # 日付のみ抽出
        else:
            # 日付のみ（日足データ）
            df['date'] = df['日付'].apply(parse_date)
    else:
        print(f"WARNING: No date column in {csv_path}")
        return
    
    df = df.dropna(subset=['date'])
    
    # 価格データが全て欠損している行を除外
    price_cols = ['始値', '高値', '安値', '終値']
    df = df.dropna(subset=price_cols, how='all')
    
    if df.empty:
        print(f"WARNING: No valid data in {csv_path}")
        return
    
    # 価格帯別出来高を計算
    bin_size = 1.0 if timeframe == '日足' else 0.5  # 日足は1円刻み、分足は0.5円刻み
    
    # 3分足の場合は日ごとに揉み合い価格帯を検出
    if timeframe == '3分足' and 'date_only' in df.columns:
        all_consolidation_zones = []
        daily_volume_profiles = {}
        
        for date_val in sorted(df['date_only'].unique()):
            df_day = df[df['date_only'] == date_val]
            volume_profile_day = calculate_volume_profile(df_day, bin_size)
            daily_volume_profiles[date_val] = volume_profile_day
            
            consolidation_zones_day = detect_consolidation_zones(volume_profile_day, threshold_percentile=70, min_width=3)
            
            # 日付情報を追加
            for zone_start, zone_end in consolidation_zones_day:
                all_consolidation_zones.append((date_val, zone_start, zone_end))
        
        # 全期間の価格帯別出来高（右側グラフ用）
        volume_profile = calculate_volume_profile(df, bin_size)
        
        print(f"{symbol} {timeframe}: {len(df)}件 ({df['date'].min()} ~ {df['date'].max()})")
        print(f"  日数: {len(df['date_only'].unique())}日")
        print(f"  揉み合い価格帯: {len(all_consolidation_zones)}箇所（日別）")
    else:
        # 日足の場合は全期間で計算
        volume_profile = calculate_volume_profile(df, bin_size)
        consolidation_zones = detect_consolidation_zones(volume_profile, threshold_percentile=70, min_width=3)
        all_consolidation_zones = [(None, start, end) for start, end in consolidation_zones]
        
        print(f"{symbol} {timeframe}: {len(df)}件 ({df['date'].min()} ~ {df['date'].max()})")
        print(f"  揉み合い価格帯: {len(consolidation_zones)}箇所")
    
    # プロット作成（3列レイアウト: OHLC | 価格帯別出来高 | 出来高）
    fig = plt.figure(figsize=(18, 10))
    gs = fig.add_gridspec(2, 2, width_ratios=[4, 1], height_ratios=[3, 1], hspace=0.05, wspace=0.05)
    
    ax_ohlc = fig.add_subplot(gs[0, 0])  # OHLCチャート
    ax_volume_profile = fig.add_subplot(gs[0, 1], sharey=ax_ohlc)  # 価格帯別出来高
    ax_volume = fig.add_subplot(gs[1, 0], sharex=ax_ohlc)  # 時系列出来高
    
    # OHLCキャンドルスティック
    bar_width = (df['date'].max() - df['date'].min()).total_seconds() / len(df) / 86400 * 0.6
    
    for idx, row in df.iterrows():
        date = row['date']
        open_price = row['始値'] if '始値' in row else None
        high = row['高値'] if '高値' in row else None
        low = row['安値'] if '安値' in row else None
        close = row['終値'] if '終値' in row else None
        
        if pd.isna(open_price) or pd.isna(close):
            continue
        
        color = 'red' if close >= open_price else 'blue'
        
        # ローソク足の実体
        ax_ohlc.plot([date, date], [open_price, close], color=color, linewidth=4, solid_capstyle='butt')
        
        # ヒゲ
        if not pd.isna(high):
            ax_ohlc.plot([date, date], [max(open_price, close), high], color=color, linewidth=1)
        if not pd.isna(low):
            ax_ohlc.plot([date, date], [min(open_price, close), low], color=color, linewidth=1)
    
    # 揉み合い価格帯を描画
    colors = plt.cm.tab20(np.linspace(0, 1, 20))
    color_idx = 0
    
    for zone_info in all_consolidation_zones:
        if len(zone_info) == 3:
            # 日別揉み合い（3分足）- 全期間に水平線を引く
            date_val, zone_start, zone_end = zone_info
            
            color = colors[color_idx % len(colors)]
            
            # 価格帯を半透明の帯として全期間に表示
            ax_ohlc.axhspan(zone_start, zone_end, alpha=0.15, facecolor=color, edgecolor=color, linewidth=0.5)
            
            # 中心線を全期間に引く
            center_price = (zone_start + zone_end) / 2
            ax_ohlc.axhline(y=center_price, color=color, linestyle='--', linewidth=1.5, alpha=0.7, 
                          label=f'{date_val}: {center_price:.1f}円')
            
            color_idx += 1
        else:
            # 全期間揉み合い（日足）
            _, zone_start, zone_end = zone_info
            ax_ohlc.axhspan(zone_start, zone_end, alpha=0.2, color='orange')
            ax_ohlc.axhline(y=(zone_start + zone_end) / 2, color='orange', linestyle='--', linewidth=1, alpha=0.5)
    
    ax_ohlc.set_ylabel('価格', fontsize=12)
    ax_ohlc.set_title(f'{symbol} - {timeframe} (揉み合い価格帯: {len(all_consolidation_zones)}箇所)', 
                      fontsize=14, fontweight='bold')
    ax_ohlc.grid(True, alpha=0.3)
    ax_ohlc.tick_params(labelbottom=False)
    
    # 価格帯別出来高を描画
    if volume_profile:
        prices = sorted(volume_profile.keys())
        volumes = [volume_profile[p] for p in prices]
        
        ax_volume_profile.barh(prices, volumes, height=bin_size*0.8, color='gray', alpha=0.5)
        ax_volume_profile.set_xlabel('出来高', fontsize=10)
        ax_volume_profile.tick_params(labelleft=False)
        ax_volume_profile.grid(True, alpha=0.3, axis='y')
        
        # VPOCを表示
        vpoc_price = max(volume_profile, key=volume_profile.get)
        ax_volume_profile.axhline(y=vpoc_price, color='red', linestyle='-', linewidth=2, label='VPOC')
        ax_ohlc.axhline(y=vpoc_price, color='red', linestyle='-', linewidth=1, alpha=0.7)
    
    # 時系列出来高
    if '出来高' in df.columns:
        ax_volume.bar(df['date'], df['出来高'], color='gray', alpha=0.5, width=bar_width)
        ax_volume.set_ylabel('出来高', fontsize=12)
        ax_volume.grid(True, alpha=0.3)
    
    # X軸フォーマット
    if timeframe == '日足':
        ax_volume.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    else:
        ax_volume.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        ax_volume.xaxis.set_major_locator(mdates.AutoDateLocator())
    
    plt.setp(ax_volume.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 保存
    fig_path = os.path.join(FIG_DIR, f"{symbol}_{timeframe}_with_volume_profile.png")
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  Saved: {fig_path}")

def main():
    print("=== チャートデータ可視化 ===\n")
    
    # 日足データ
    print("【日足】")
    day_dir = os.path.join(OUTPUT_DIR, 'D_3000_20260119')
    if os.path.exists(day_dir):
        for csv_file in glob.glob(os.path.join(day_dir, '*.csv')):
            symbol = os.path.basename(csv_file).split('_')[3]
            visualize_ohlc(csv_file, symbol, '日足')
    else:
        print(f"  WARNING: {day_dir} not found")
    
    print()
    
    # 3分足データ
    print("【3分足】")
    min3_dir = os.path.join(OUTPUT_DIR, '3M_3000_20260119')
    if os.path.exists(min3_dir):
        for csv_file in glob.glob(os.path.join(min3_dir, '*.csv')):
            symbol = os.path.basename(csv_file).split('_')[3]
            visualize_ohlc(csv_file, symbol, '3分足')
    else:
        print(f"  WARNING: {min3_dir} not found")
    
    print()
    print(f"=== 完了 ===")
    print(f"チャート保存先: {FIG_DIR}")

if __name__ == "__main__":
    main()
