from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd


@dataclass
class SupportZone:
    price: float
    lower: float
    upper: float
    strength: float  # 出来高等の強さ


def volume_profile_support(
    intraday: pd.DataFrame,
    n_nodes: int = 5,
    lookback_days: int = 2,
    band_pct: float = 0.002,
) -> List[SupportZone]:
    # 直近lookback_daysの立会時間のデータを抽出
    intraday = intraday.copy()
    intraday["date"] = intraday["datetime"].dt.date
    last_dates = sorted(intraday["date"].unique())[-lookback_days:]
    df = intraday[intraday["date"].isin(last_dates)]
    if df.empty:
        return []

    prices = df["close"].values
    vols = df["volume"].values
    # 価格帯別出来高: 価格をビンに、出来高を加算
    price_min, price_max = prices.min(), prices.max()
    bins = max(50, int((price_max - price_min) / max(1.0, price_min * 0.002)))
    hist, edges = np.histogram(prices, bins=bins, weights=vols)
    # 上位n_nodesの価格帯を抽出
    idxs = np.argsort(hist)[-n_nodes:][::-1]
    zones: List[SupportZone] = []
    for i in idxs:
        center = (edges[i] + edges[i + 1]) / 2
        band = max(band_pct * center, 1.0)
        zones.append(SupportZone(price=center, lower=center - band, upper=center + band, strength=float(hist[i])))
    # 価格が近い帯を統合
    zones = merge_close_zones(zones)
    return zones


def merge_close_zones(zones: List[SupportZone], merge_gap: float = 0.002) -> List[SupportZone]:
    if not zones:
        return zones
    zones = sorted(zones, key=lambda z: z.price)
    merged: List[SupportZone] = []
    cur = zones[0]
    for z in zones[1:]:
        if z.lower <= cur.upper + cur.price * merge_gap:
            cur = SupportZone(
                price=(cur.price + z.price) / 2,
                lower=min(cur.lower, z.lower),
                upper=max(cur.upper, z.upper),
                strength=cur.strength + z.strength,
            )
        else:
            merged.append(cur)
            cur = z
    merged.append(cur)
    return merged


def swing_points(daily: pd.DataFrame, lookback: int = 5) -> Tuple[pd.Series, pd.Series]:
    highs = daily["high"].rolling(lookback * 2 + 1, center=True).apply(lambda x: float(x.argmax()) == lookback)
    lows = daily["low"].rolling(lookback * 2 + 1, center=True).apply(lambda x: float(x.argmin()) == lookback)
    swing_high = daily["high"].where(highs == 1.0)
    swing_low = daily["low"].where(lows == 1.0)
    return swing_high, swing_low


def recent_horizontal_support(daily: pd.DataFrame, lookback: int = 5, n_levels: int = 3) -> List[float]:
    _, swing_low = swing_points(daily, lookback)
    levels = swing_low.dropna().tail(10).sort_values(ascending=False).head(n_levels)
    return levels.tolist()
