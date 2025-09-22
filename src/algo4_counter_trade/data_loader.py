from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd


JP_COLS = {
    "dt": "日付",
    "time": "時刻",
    "datetime": "日時",
    "open": "始値",
    "high": "高値",
    "low": "安値",
    "close": "終値",
    "volume": "出来高",
}


@dataclass
class LoadedData:
    intraday: pd.DataFrame
    daily: Optional[pd.DataFrame]


def _parse_datetime(df: pd.DataFrame) -> pd.Series:
    if JP_COLS["datetime"] in df.columns:
        return pd.to_datetime(df[JP_COLS["datetime"]])
    elif JP_COLS["dt"] in df.columns and JP_COLS["time"] in df.columns:
        return pd.to_datetime(df[JP_COLS["dt"]] + " " + df[JP_COLS["time"]])
    else:
        raise ValueError("日時/日付+時刻のカラムが見つかりません")


def load_intraday_csv(path: str, tz: str = "Asia/Tokyo") -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    dt = _parse_datetime(df)
    df = df.assign(datetime=dt.dt.tz_localize(tz, nonexistent="shift_forward", ambiguous="NaT"))
    cols = {
        JP_COLS["open"]: "open",
        JP_COLS["high"]: "high",
        JP_COLS["low"]: "low",
        JP_COLS["close"]: "close",
        JP_COLS["volume"]: "volume",
    }
    df = df.rename(columns=cols)
    return df[["datetime", "open", "high", "low", "close", "volume"]].dropna()


def resample_to_minutes(df: pd.DataFrame, minutes: int = 3) -> pd.DataFrame:
    g = df.set_index("datetime").sort_index()
    rule = f"{minutes}T"
    ohlcv = g.resample(rule).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()
    ohlcv = ohlcv.reset_index()
    return ohlcv


def load_daily_csv(path: str, tz: str = "Asia/Tokyo") -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    # 日足は日付のみ想定
    if JP_COLS["dt"] in df.columns:
        dt = pd.to_datetime(df[JP_COLS["dt"]]).dt.tz_localize(tz)
    else:
        dt = _parse_datetime(df)
    cols = {
        JP_COLS["open"]: "open",
        JP_COLS["high"]: "high",
        JP_COLS["low"]: "low",
        JP_COLS["close"]: "close",
        JP_COLS["volume"]: "volume",
    }
    df = df.rename(columns=cols)
    df = df.assign(datetime=dt)
    return df[["datetime", "open", "high", "low", "close", "volume"]].dropna().sort_values("datetime")
