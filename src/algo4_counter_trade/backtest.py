from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any

import pandas as pd


@dataclass
class Trade:
    action: str
    idx: int
    price: float
    reason: str


def evaluate_trades(df: pd.DataFrame, trades: List[Dict[str, Any]], size: int = 100, fee_pct: float = 0.0, slippage_pct: float = 0.0) -> pd.DataFrame:
    rows = []
    position_price = None
    for t in trades:
        row = df.iloc[t["idx"]]
        exec_price = float(t["price"]) * (1 + slippage_pct if t["action"] == "buy" else 1 - slippage_pct)
        fee = exec_price * size * fee_pct
        if t["action"] == "buy":
            position_price = exec_price
            pnl = 0.0
        else:
            pnl = (exec_price - (position_price or exec_price)) * size - fee
            position_price = None
        rows.append({
            "datetime": row["datetime"],
            "action": t["action"],
            "price": exec_price,
            "reason": t.get("reason", ""),
            "fee": fee,
            "pnl": pnl,
        })
    return pd.DataFrame(rows)


def plot_trades(df: pd.DataFrame, trades_df: pd.DataFrame):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    ax[0].plot(df["datetime"], df["close"], color="black", label="Close")
    buys = trades_df[trades_df["action"] == "buy"]
    sells = trades_df[trades_df["action"] == "sell"]
    ax[0].scatter(buys["datetime"], buys["price"], marker="^", color="green", label="Buy")
    ax[0].scatter(sells["datetime"], sells["price"], marker="v", color="red", label="Sell")
    ax[0].legend(); ax[0].grid(True)

    cum_pnl = trades_df["pnl"].cumsum()
    ax[1].plot(trades_df["datetime"], cum_pnl, color="blue", label="Cumulative PnL")
    ax[1].legend(); ax[1].grid(True)
    plt.tight_layout(); plt.show()
