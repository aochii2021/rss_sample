from __future__ import annotations

from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd

from .support import SupportZone


def plot_intraday_with_support(df3: pd.DataFrame, zones: List[SupportZone], trades_df: Optional[pd.DataFrame] = None):
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df3["datetime"], df3["close"], color="black", label="Close")
    for z in zones:
        ax.axhspan(z.lower, z.upper, color="green", alpha=0.1)
    if trades_df is not None and not trades_df.empty:
        buys = trades_df[trades_df["action"] == "buy"]
        sells = trades_df[trades_df["action"] == "sell"]
        ax.scatter(buys["datetime"], buys["price"], marker="^", color="green", label="Buy")
        ax.scatter(sells["datetime"], sells["price"], marker="v", color="red", label="Sell")
    ax.legend(); ax.grid(True); plt.tight_layout(); plt.show()


def plot_daily_support(daily: pd.DataFrame, levels: List[float]):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(daily["datetime"], daily["close"], color="black", label="Close(D)")
    for lv in levels:
        ax.axhline(lv, color="blue", alpha=0.3, linestyle=":")
    ax.legend(); ax.grid(True); plt.tight_layout(); plt.show()
