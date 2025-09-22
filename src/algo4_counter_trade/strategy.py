from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import pandas as pd

from .config import StrategyConfig
from .support import SupportZone


@dataclass
class Position:
    entry_price: float
    size: int
    entry_idx: int


def generate_signals(
    df3: pd.DataFrame,
    zones: List[SupportZone],
    cfg: StrategyConfig,
) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    pos: Optional[Position] = None
    trades_today = 0

    for i, row in enumerate(df3.itertuples(index=False)):
        price = float(row.close)
        # エントリー条件: 価格がいずれかのサポート帯に入り、直近で下落→反発の兆し（単純に陽線確認）
        in_zone = any(z.lower <= price <= z.upper for z in zones)
        is_bullish = float(row.close) >= float(row.open)

        # EODフラット条件（14:55以降などは建てない/クローズ）
        ts = getattr(row, "datetime")
        minute = ts.minute + ts.hour * 60
        eod_cut_minute = 14 * 60 + 55

        if pos is not None:
            # 損切り/利確
            stop = pos.entry_price * (1 - cfg.stop_pct)
            take = pos.entry_price * (1 + (cfg.take_pct if cfg.take_pct is not None else cfg.stop_pct * cfg.risk_rr))
            if price <= stop:
                trades.append({"action": "sell", "idx": i, "price": price, "reason": "stop"})
                pos = None
            elif price >= take:
                trades.append({"action": "sell", "idx": i, "price": price, "reason": "take"})
                pos = None
            elif minute >= eod_cut_minute:
                trades.append({"action": "sell", "idx": i, "price": price, "reason": "eod"})
                pos = None
        else:
            if trades_today < cfg.max_trades_per_day and in_zone and is_bullish and minute < eod_cut_minute:
                trades.append({"action": "buy", "idx": i, "price": price, "reason": "support_rebound"})
                pos = Position(entry_price=price, size=1, entry_idx=i)
                trades_today += 1

        # 日付を跨いだら日計をリセット
        if i > 0:
            prev = df3.iloc[i - 1]
            if prev["datetime"].date() != ts.date():
                trades_today = 0
                if pos is not None:
                    trades.append({"action": "sell", "idx": i, "price": price, "reason": "new_day_force_flat"})
                    pos = None

    # 終了時にポジションがあればクローズ（保険）
    if pos is not None:
        last_price = float(df3.iloc[-1]["close"])
        trades.append({"action": "sell", "idx": len(df3) - 1, "price": last_price, "reason": "end_force_flat"})

    return trades
