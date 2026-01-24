#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分足OHLCからサポート/レジスタンスレベルを抽出します。
出力: JSONL形式（1行=1レベル）
"""
import argparse
import json
import glob
import os
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from collections import Counter

def read_ohlc(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

def find_recent_high_low(df: pd.DataFrame, lookback_bars: int = 180, symbol: str = "") -> List[Dict[str, Any]]:
    """直近N本の高値・安値を抽出"""
    recent = df.tail(lookback_bars)
    if len(recent) == 0:
        return []
    
    levels = []
    
    # 直近高値
    high_val = recent["high"].max()
    high_idx = recent["high"].idxmax()
    high_ts = recent.loc[high_idx, "timestamp"].isoformat()
    
    # タッチ回数（高値付近）
    touch_high = ((recent["high"] >= high_val * 0.998) & (recent["high"] <= high_val * 1.002)).sum()
    
    levels.append({
        "kind": "recent_high",
        "symbol": symbol,
        "anchors": [[high_ts, float(high_val)]],
        "slope": 0.0,
        "level_now": float(high_val),
        "strength": min(touch_high / 10.0, 1.0),
        "meta": {"lookback_bars": lookback_bars}
    })
    
    # 直近安値
    low_val = recent["low"].min()
    low_idx = recent["low"].idxmin()
    low_ts = recent.loc[low_idx, "timestamp"].isoformat()
    
    touch_low = ((recent["low"] >= low_val * 0.998) & (recent["low"] <= low_val * 1.002)).sum()
    
    levels.append({
        "kind": "recent_low",
        "symbol": symbol,
        "anchors": [[low_ts, float(low_val)]],
        "slope": 0.0,
        "level_now": float(low_val),
        "strength": min(touch_low / 10.0, 1.0),
        "meta": {"lookback_bars": lookback_bars}
    })
    
    return levels

def find_vpoc_hvn(df: pd.DataFrame, bin_size: float = 1.0, top_n: int = 3, symbol: str = "") -> List[Dict[str, Any]]:
    """価格帯別出来高（VPOC/HVN）を抽出"""
    if len(df) == 0 or "volume" not in df.columns:
        return []
    
    levels = []
    price_volume = {}
    
    for _, row in df.iterrows():
        low, high, vol = row["low"], row["high"], row["volume"]
        if pd.isna(low) or pd.isna(high) or pd.isna(vol) or vol <= 0:
            continue
        
        # 価格帯に出来高を均等配分
        num_bins = max(1, int((high - low) / bin_size) + 1)
        vol_per_bin = vol / num_bins
        
        for i in range(num_bins):
            price = low + i * bin_size
            price_key = round(price / bin_size) * bin_size
            price_volume[price_key] = price_volume.get(price_key, 0) + vol_per_bin
    
    if not price_volume:
        return []
    
    # 上位N個のピークを抽出
    sorted_pv = sorted(price_volume.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    for rank, (price, volume) in enumerate(sorted_pv):
        kind = "vpoc" if rank == 0 else "hvn"
        strength = volume / sorted_pv[0][1] if sorted_pv else 0.0
        
        levels.append({
            "kind": kind,
            "symbol": symbol,
            "anchors": [["", float(price)]],
            "slope": 0.0,
            "level_now": float(price),
            "strength": strength,
            "meta": {"bin_size": bin_size, "volume": float(volume), "rank": rank}
        })
    
    return levels

def find_consolidation_zones(df: pd.DataFrame, window: int = 60, price_tolerance: float = 0.01, 
                            min_bars: int = 20, symbol: str = "") -> List[Dict[str, Any]]:
    """
    コンソリデーションゾーン（揉んだ場所）を検出
    
    Args:
        window: ローリングウィンドウのサイズ（バー数）
        price_tolerance: 価格変動の許容範囲（0.01 = ±1%）
        min_bars: 最低継続時間（バー数）
        symbol: 銘柄コード
    
    Returns:
        検出されたコンソリデーションゾーンのリスト
    """
    if len(df) < window:
        return []
    
    levels = []
    df = df.copy()
    df = df.reset_index(drop=True)
    
    # ローリングウィンドウで価格レンジを計算
    for i in range(window, len(df)):
        window_data = df.iloc[i-window:i]
        high_max = window_data["high"].max()
        low_min = window_data["low"].min()
        mid_price = (high_max + low_min) / 2
        price_range = high_max - low_min
        
        # 価格変動が小さい（揉んでいる）場合
        if price_range / mid_price <= price_tolerance:
            # 十分な期間継続しているか確認
            if len(window_data) >= min_bars:
                levels.append({
                    "kind": "consolidation",
                    "symbol": symbol,
                    "anchors": [["", float(mid_price)]],
                    "slope": 0.0,
                    "level_now": float(mid_price),
                    "strength": min(len(window_data) / 100.0, 1.0),  # 継続期間に比例
                    "meta": {
                        "high": float(high_max),
                        "low": float(low_min),
                        "range_pct": float(price_range / mid_price * 100),
                        "duration_bars": len(window_data)
                    }
                })
    
    # 重複を削除（同じ価格帯のゾーンをマージ）
    if levels:
        df_levels = pd.DataFrame(levels)
        df_levels = df_levels.sort_values('strength', ascending=False)
        unique_levels = []
        for _, level in df_levels.iterrows():
            is_duplicate = False
            for unique in unique_levels:
                if abs(level['level_now'] - unique['level_now']) / level['level_now'] < 0.005:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_levels.append(level.to_dict())
        return unique_levels[:5]  # 上位5個まで
    
    return levels

def find_multi_day_vpoc(df: pd.DataFrame, bin_size: float = 1.0, lookback_days: int = 5, 
                        top_n: int = 3, symbol: str = "") -> List[Dict[str, Any]]:
    """
    複数日の価格帯別出来高（VPOC/HVN）を抽出
    
    Args:
        df: OHLC+volumeデータ
        bin_size: 価格ビンのサイズ
        lookback_days: 過去何日分を集計するか
        top_n: 上位何個を抽出するか
        symbol: 銘柄コード
    
    Returns:
        検出された出来高集中価格帯のリスト
    """
    if len(df) == 0 or "volume" not in df.columns:
        return []
    
    # 日付列を追加
    df = df.copy()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    
    # 指定日数分のデータを使用
    unique_dates = sorted(df["date"].unique())
    if len(unique_dates) > lookback_days:
        target_dates = unique_dates[-lookback_days:]
        df = df[df["date"].isin(target_dates)]
    
    # 価格帯別に出来高を集計
    price_volume = {}
    for _, row in df.iterrows():
        low, high, vol = row["low"], row["high"], row["volume"]
        if pd.isna(low) or pd.isna(high) or pd.isna(vol) or vol <= 0:
            continue
        
        num_bins = max(1, int((high - low) / bin_size) + 1)
        vol_per_bin = vol / num_bins
        
        for i in range(num_bins):
            price = low + i * bin_size
            price_key = round(price / bin_size) * bin_size
            price_volume[price_key] = price_volume.get(price_key, 0) + vol_per_bin
    
    if not price_volume:
        return []
    
    # 上位N個のピークを抽出
    sorted_pv = sorted(price_volume.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    levels = []
    for rank, (price, volume) in enumerate(sorted_pv):
        kind = "multi_day_vpoc" if rank == 0 else "multi_day_hvn"
        strength = volume / sorted_pv[0][1] if sorted_pv else 0.0
        
        levels.append({
            "kind": kind,
            "symbol": symbol,
            "anchors": [["", float(price)]],
            "slope": 0.0,
            "level_now": float(price),
            "strength": strength,
            "meta": {
                "bin_size": bin_size,
                "volume": float(volume),
                "rank": rank,
                "lookback_days": len(df["date"].unique())
            }
        })
    
    return levels

def find_consolidation_from_daily_chart(chart_dir: str, symbol: str, bin_size: float = 1.0, 
                                        threshold_percentile: int = 70, min_width: int = 3,
                                        exclude_date_after: str = None) -> List[Dict[str, Any]]:
    """
    日足チャートから揉み合い価格帯を検出
    
    Args:
        chart_dir: チャートデータディレクトリ
        symbol: 銘柄コード
        bin_size: 価格帯の幅
        threshold_percentile: 出来高閾値パーセンタイル
        min_width: 最小連続価格帯数
        exclude_date_after: この日付以降のデータを除外（YYYY-MM-DD形式、データリーク防止）
    
    Returns:
        サポート/レジスタンスレベルのリスト
    """
    # 日足データを検索
    pattern = os.path.join(chart_dir, f"stock_chart_D_{symbol}_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        return []
    
    df = pd.read_csv(files[0], encoding='utf-8-sig')
    
    if df.empty:
        return []
    
    # データリーク防止：指定日以降のデータを除外
    if exclude_date_after and '日付' in df.columns:
        df['日付'] = pd.to_datetime(df['日付'])
        exclude_dt = pd.to_datetime(exclude_date_after)
        before_count = len(df)
        df = df[df['日付'] < exclude_dt].copy()
        print(f"  [{symbol}] 日足: {before_count}行 → {len(df)}行（{exclude_date_after}以降を除外）", flush=True)
    
    # 価格帯別出来高を計算
    volume_profile = {}
    for _, row in df.iterrows():
        high = row.get('高値')
        low = row.get('安値')
        volume = row.get('出来高', 0)
        
        if pd.isna(high) or pd.isna(low) or pd.isna(volume) or volume == 0:
            continue
        
        min_price = int(low / bin_size) * bin_size
        max_price = int(high / bin_size) * bin_size + bin_size
        price_range = np.arange(min_price, max_price, bin_size)
        vol_per_bin = volume / len(price_range) if len(price_range) > 0 else 0
        
        for price in price_range:
            volume_profile[price] = volume_profile.get(price, 0) + vol_per_bin
    
    if not volume_profile:
        return []
    
    # 揉み合い価格帯を検出
    sorted_prices = sorted(volume_profile.keys())
    volumes = [volume_profile[p] for p in sorted_prices]
    threshold = np.percentile(volumes, threshold_percentile)
    
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
                    zones.append((zone_start, zone_end, volume_profile[zone_start]))
                zone_start = None
    
    if zone_start is not None:
        zone_end = sorted_prices[-1]
        if (len(sorted_prices) - sorted_prices.index(zone_start)) >= min_width:
            zones.append((zone_start, zone_end, volume_profile[zone_start]))
    
    # レベルとして出力
    levels = []
    for zone_start, zone_end, volume in zones:
        center_price = (zone_start + zone_end) / 2
        # 揉み合いレベルは強度を1.5倍に（上限1.0）
        base_strength = volume / max(volumes) if volumes else 0.0
        strength = min(1.0, base_strength * 1.5)
        
        levels.append({
            "kind": "daily_consolidation",
            "symbol": symbol,
            "anchors": [["", float(center_price)]],
            "slope": 0.0,
            "level_now": float(center_price),
            "strength": strength,
            "meta": {
                "zone_start": float(zone_start),
                "zone_end": float(zone_end),
                "zone_width": float(zone_end - zone_start),
                "volume": float(volume),
                "source": "daily_chart"
            }
        })
    
    return levels

def find_consolidation_from_intraday_chart(chart_dir: str, symbol: str, bin_size: float = 0.5,
                                          threshold_percentile: int = 70, min_width: int = 3,
                                          exclude_date_after: str = None) -> List[Dict[str, Any]]:
    """
    分足チャートから日別の揉み合い価格帯を検出
    
    Args:
        chart_dir: チャートデータディレクトリ
        symbol: 銘柄コード
        bin_size: 価格帯の幅
        threshold_percentile: 出来高閾値パーセンタイル
        min_width: 最小連続価格帯数
        exclude_date_after: この日付以降のデータを除外（YYYY-MM-DD形式、データリーク防止）
        threshold_percentile: 出来高閾値パーセンタイル
        min_width: 最小連続価格帯数
    
    Returns:
        サポート/レジスタンスレベルのリスト
    """
    # 3分足データを検索
    pattern = os.path.join(chart_dir, f"stock_chart_3M_{symbol}_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        return []
    
    df = pd.read_csv(files[0], encoding='utf-8-sig')
    
    if df.empty or '日付' not in df.columns:
        return []
    
    # 日付列を追加
    if '時刻' in df.columns:
        df['datetime'] = pd.to_datetime(df['日付'] + ' ' + df['時刻'], format='%Y/%m/%d %H:%M', errors='coerce')
    else:
        df['datetime'] = pd.to_datetime(df['日付'], errors='coerce')
    
    # データリーク防止：指定日以降のデータを除外
    if exclude_date_after and 'datetime' in df.columns:
        exclude_dt = pd.to_datetime(exclude_date_after)
        before_count = len(df)
        df = df[df['datetime'] < exclude_dt].copy()
        print(f"  [{symbol}] 分足: {before_count}行 → {len(df)}行（{exclude_date_after}以降を除外）", flush=True)
    
    if df.empty:
        return []
    
    df['日付'] = pd.to_datetime(df['日付'])
    if 'datetime' in df.columns:
        df['date'] = df['datetime'].dt.date
    else:
        return []
    
    df = df.dropna(subset=['date'])
    
    levels = []
    
    # 日別に揉み合い価格帯を検出
    for date_val in sorted(df['date'].unique()):
        df_day = df[df['date'] == date_val]
        
        # 価格帯別出来高を計算
        volume_profile = {}
        for _, row in df_day.iterrows():
            high = row.get('高値')
            low = row.get('安値')
            volume = row.get('出来高', 0)
            
            if pd.isna(high) or pd.isna(low) or pd.isna(volume) or volume == 0:
                continue
            
            min_price = int(low / bin_size) * bin_size
            max_price = int(high / bin_size) * bin_size + bin_size
            price_range = np.arange(min_price, max_price, bin_size)
            vol_per_bin = volume / len(price_range) if len(price_range) > 0 else 0
            
            for price in price_range:
                volume_profile[price] = volume_profile.get(price, 0) + vol_per_bin
        
        if not volume_profile:
            continue
        
        # 揉み合い価格帯を検出
        sorted_prices = sorted(volume_profile.keys())
        volumes = [volume_profile[p] for p in sorted_prices]
        threshold = np.percentile(volumes, threshold_percentile)
        
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
                        zones.append((zone_start, zone_end, volume_profile[zone_start]))
                    zone_start = None
        
        if zone_start is not None:
            zone_end = sorted_prices[-1]
            if (len(sorted_prices) - sorted_prices.index(zone_start)) >= min_width:
                zones.append((zone_start, zone_end, volume_profile[zone_start]))
        
        # レベルとして出力
        for zone_start, zone_end, volume in zones:
            center_price = (zone_start + zone_end) / 2
            # 揉み合いレベルは強度を1.5倍に（上限1.0）
            base_strength = volume / max(volumes) if volumes else 0.0
            strength = min(1.0, base_strength * 1.5)
            
            levels.append({
                "kind": "intraday_consolidation",
                "symbol": symbol,
                "anchors": [["", float(center_price)]],
                "slope": 0.0,
                "level_now": float(center_price),
                "strength": strength,
                "meta": {
                    "zone_start": float(zone_start),
                    "zone_end": float(zone_end),
                    "zone_width": float(zone_end - zone_start),
                    "volume": float(volume),
                    "date": str(date_val),
                    "source": "3min_chart"
                }
            })
    
    return levels

def find_swing_levels(df: pd.DataFrame, left: int = 3, right: int = 3, symbol: str = "") -> List[Dict[str, Any]]:
    """スイング高値・安値（フラクタル）を検出"""
    if len(df) < left + right + 1:
        return []
    
    levels = []
    
    # スイング高値
    for i in range(left, len(df) - right):
        is_swing_high = True
        center_high = df.iloc[i]["high"]
        
        for j in range(i - left, i):
            if df.iloc[j]["high"] >= center_high:
                is_swing_high = False
                break
        for j in range(i + 1, i + right + 1):
            if df.iloc[j]["high"] >= center_high:
                is_swing_high = False
                break
        
        if is_swing_high:
            ts = df.iloc[i]["timestamp"].isoformat()
            levels.append({
                "kind": "swing_resistance",
                "symbol": symbol,
                "anchors": [[ts, float(center_high)]],
                "slope": 0.0,
                "level_now": float(center_high),
                "strength": 0.7,
                "meta": {"pivot_left": left, "pivot_right": right}
            })
    
    # スイング安値
    for i in range(left, len(df) - right):
        is_swing_low = True
        center_low = df.iloc[i]["low"]
        
        for j in range(i - left, i):
            if df.iloc[j]["low"] <= center_low:
                is_swing_low = False
                break
        for j in range(i + 1, i + right + 1):
            if df.iloc[j]["low"] <= center_low:
                is_swing_low = False
                break
        
        if is_swing_low:
            ts = df.iloc[i]["timestamp"].isoformat()
            levels.append({
                "kind": "swing_support",
                "symbol": symbol,
                "anchors": [[ts, float(center_low)]],
                "slope": 0.0,
                "level_now": float(center_low),
                "strength": 0.7,
                "meta": {"pivot_left": left, "pivot_right": right}
            })
    
    return levels

def find_prev_day_levels(df: pd.DataFrame, symbol: str = "") -> List[Dict[str, Any]]:
    """前日高値・安値・終値を抽出"""
    if len(df) == 0:
        return []
    
    df = df.copy()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    
    unique_dates = sorted(df["date"].unique())
    if len(unique_dates) < 2:
        return []
    
    prev_date = unique_dates[-2]
    prev_day = df[df["date"] == prev_date]
    
    if len(prev_day) == 0:
        return []
    
    levels = []
    
    prev_high = prev_day["high"].max()
    prev_low = prev_day["low"].min()
    prev_close = prev_day.iloc[-1]["close"]
    
    levels.append({
        "kind": "prev_high",
        "symbol": symbol,
        "anchors": [["", float(prev_high)]],
        "slope": 0.0,
        "level_now": float(prev_high),
        "strength": 0.8,
        "meta": {"day": str(prev_date)}
    })
    
    levels.append({
        "kind": "prev_low",
        "symbol": symbol,
        "anchors": [["", float(prev_low)]],
        "slope": 0.0,
        "level_now": float(prev_low),
        "strength": 0.8,
        "meta": {"day": str(prev_date)}
    })
    
    levels.append({
        "kind": "prev_close",
        "symbol": symbol,
        "anchors": [["", float(prev_close)]],
        "slope": 0.0,
        "level_now": float(prev_close),
        "strength": 0.6,
        "meta": {"day": str(prev_date)}
    })
    
    return levels

def find_psychological_levels(price_min: float, price_max: float, symbol: str = "",
                             round_levels: List[int] = [100, 50, 10]) -> List[Dict[str, Any]]:
    """
    キリの良い数字（心理的節目）を検出
    
    Args:
        price_min: 価格の最小値
        price_max: 価格の最大値
        symbol: 銘柄コード
        round_levels: 検出する単位（例: [100, 50, 10]円単位）
    
    Returns:
        心理的サポート/レジスタンスレベルのリスト
    """
    levels = []
    
    for unit in round_levels:
        # 価格範囲内のキリの良い数字を列挙
        start = int(price_min / unit) * unit
        end = int(price_max / unit + 1) * unit
        
        for price in range(start, end + 1, unit):
            if price_min <= price <= price_max:
                # 大きな単位ほど強度を高く
                strength = 0.3 + (0.4 * (unit / max(round_levels)))
                
                levels.append({
                    "kind": "psychological",
                    "symbol": symbol,
                    "anchors": [["", float(price)]],
                    "slope": 0.0,
                    "level_now": float(price),
                    "strength": min(1.0, strength),
                    "meta": {
                        "unit": unit,
                        "source": "round_number"
                    }
                })
    
    return levels

def find_support_resistance_lines(df_chart: pd.DataFrame, symbol: str = "",
                                  lookback_days: int = 20,
                                  prominence: float = 0.02) -> List[Dict[str, Any]]:
    """
    高値・安値からレジスタンス・サポートラインを検出
    
    Args:
        df_chart: チャートデータ（日足または分足）
        symbol: 銘柄コード
        lookback_days: 検出対象の日数
        prominence: ピーク検出の顕著性（価格の何%以上の差）
    
    Returns:
        サポート/レジスタンスレベルのリスト
    """
    from scipy.signal import find_peaks
    
    if len(df_chart) < 10:
        return []
    
    levels = []
    
    # 高値からレジスタンスを検出
    highs = df_chart['高値'].values
    prominence_abs = np.mean(highs) * prominence
    peaks_high, properties_high = find_peaks(highs, prominence=prominence_abs, distance=3)
    
    for idx in peaks_high:
        if idx >= len(df_chart):
            continue
        price = float(highs[idx])
        date = df_chart.iloc[idx]['日付'] if '日付' in df_chart.columns else ""
        
        # タッチ回数を計算（±0.5%の範囲）
        touch_count = ((df_chart['高値'] >= price * 0.995) & 
                      (df_chart['高値'] <= price * 1.005)).sum()
        
        strength = min(1.0, 0.5 + (touch_count * 0.1))
        
        levels.append({
            "kind": "resistance",
            "symbol": symbol,
            "anchors": [[str(date), float(price)]],
            "slope": 0.0,
            "level_now": float(price),
            "strength": strength,
            "meta": {
                "touch_count": int(touch_count),
                "source": "peak_high"
            }
        })
    
    # 安値からサポートを検出
    lows = df_chart['安値'].values
    prominence_abs = np.mean(lows) * prominence
    peaks_low, properties_low = find_peaks(-lows, prominence=prominence_abs, distance=3)
    
    for idx in peaks_low:
        if idx >= len(df_chart):
            continue
        price = float(lows[idx])
        date = df_chart.iloc[idx]['日付'] if '日付' in df_chart.columns else ""
        
        # タッチ回数を計算
        touch_count = ((df_chart['安値'] >= price * 0.995) & 
                      (df_chart['安値'] <= price * 1.005)).sum()
        
        strength = min(1.0, 0.5 + (touch_count * 0.1))
        
        levels.append({
            "kind": "support",
            "symbol": symbol,
            "anchors": [[str(date), float(price)]],
            "slope": 0.0,
            "level_now": float(price),
            "strength": strength,
            "meta": {
                "touch_count": int(touch_count),
                "source": "peak_low"
            }
        })
    
    return levels

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min1", help="minute OHLC CSV")
    ap.add_argument("--day", help="daily OHLC CSV")
    ap.add_argument("--chart-dir", help="chart data directory (for consolidation detection)")
    ap.add_argument("--out", required=True, help="output JSONL")
    ap.add_argument("--bin-size", type=float, default=1.0)
    ap.add_argument("--lookback-bars", type=int, default=180)
    ap.add_argument("--pivot-left", type=int, default=3)
    ap.add_argument("--pivot-right", type=int, default=3)
    ap.add_argument("--consolidation-window", type=int, default=60, 
                    help="consolidation zone detection window (bars)")
    ap.add_argument("--consolidation-tolerance", type=float, default=0.01,
                    help="price tolerance for consolidation detection")
    ap.add_argument("--multi-day-lookback", type=int, default=5,
                    help="lookback days for multi-day volume profile")
    ap.add_argument("--exclude-date-after", type=str, default=None,
                    help="Exclude chart data on or after this date (YYYY-MM-DD) to prevent data leakage")
    args = ap.parse_args()
    
    all_levels = []
    
    if args.min1:
        df = read_ohlc(args.min1)
        
        # 銘柄別に処理
        if "symbol" in df.columns:
            symbols = df["symbol"].unique()
            print(f"Processing {len(symbols)} symbols...", flush=True)
            for sym in symbols:
                df_sym = df[df["symbol"] == sym].copy()
                all_levels.extend(find_recent_high_low(df_sym, args.lookback_bars, str(sym)))
                all_levels.extend(find_vpoc_hvn(df_sym, args.bin_size, symbol=str(sym)))
                all_levels.extend(find_swing_levels(df_sym, args.pivot_left, args.pivot_right, str(sym)))
                all_levels.extend(find_prev_day_levels(df_sym, str(sym)))
                
                # 新機能: 数日前に揉んだ場所（consolidation zone）
                all_levels.extend(find_consolidation_zones(
                    df_sym, 
                    window=args.consolidation_window,
                    price_tolerance=args.consolidation_tolerance,
                    symbol=str(sym)
                ))
                
                # 新機能: 日足で見たときの価格帯別出来高だまり（multi-day volume profile）
                all_levels.extend(find_multi_day_vpoc(
                    df_sym,
                    bin_size=args.bin_size,
                    lookback_days=args.multi_day_lookback,
                    symbol=str(sym)
                ))
                
                # 新機能: 日足チャートから揉み合い価格帯
                if args.chart_dir:
                    all_levels.extend(find_consolidation_from_daily_chart(
                        args.chart_dir, str(sym), bin_size=1.0,
                        exclude_date_after=args.exclude_date_after
                    ))
                
                # 新機能: 分足チャートから日別揉み合い価格帯
                if args.chart_dir:
                    all_levels.extend(find_consolidation_from_intraday_chart(
                        args.chart_dir, str(sym), bin_size=0.5,
                        exclude_date_after=args.exclude_date_after
                    ))
        else:
            # 銘柄列がない場合は全体で処理
            all_levels.extend(find_recent_high_low(df, args.lookback_bars))
            all_levels.extend(find_vpoc_hvn(df, args.bin_size))
            all_levels.extend(find_swing_levels(df, args.pivot_left, args.pivot_right))
            all_levels.extend(find_prev_day_levels(df))
            all_levels.extend(find_consolidation_zones(
                df, 
                window=args.consolidation_window,
                price_tolerance=args.consolidation_tolerance
            ))
            all_levels.extend(find_multi_day_vpoc(
                df,
                bin_size=args.bin_size,
                lookback_days=args.multi_day_lookback
            ))
    
    if args.day:
        df_day = read_ohlc(args.day)
        if "symbol" in df_day.columns:
            for sym in df_day["symbol"].unique():
                df_sym = df_day[df_day["symbol"] == sym].copy()
                all_levels.extend(find_prev_day_levels(df_sym, str(sym)))
        else:
            all_levels.extend(find_prev_day_levels(df_day))
    
    # JSONL出力
    with open(args.out, "w", encoding="utf-8") as f:
        for level in all_levels:
            f.write(json.dumps(level, ensure_ascii=False) + "\n")
    
    print(f"wrote: {args.out} levels={len(all_levels)}")

if __name__ == "__main__":
    main()
