#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MarketSpeed II RSS の“生CSV”から直接、板読み特徴量を算出します（正規化なし）。
前提列:
  記録日時 (or 現在値詳細時刻/現在値時刻), 銘柄コード(任意),
  最良売気配値1..10, 最良売気配数量1..10, 最良買気配値1..10, 最良買気配数量1..10
出力列:
  ts, symbol, spread, mid, qi_l1, microprice, micro_bias, ofi_{N}, depth_imb_{k}
"""
import argparse
from datetime import datetime
import numpy as np
import pandas as pd

ENCODINGS = ["utf-8-sig", "utf-8", "cp932", "utf-16"]

def read_csv_any(path: str) -> pd.DataFrame:
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path)

def parse_ts_any(x):
    for fmt in ("%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(x), fmt)
        except Exception:
            pass
    return pd.to_datetime(x, errors="coerce")

def ensure_ts(df: pd.DataFrame,
              candidates=("記録日時","現在値詳細時刻","現在値時刻")) -> pd.DataFrame:
    ts_col = next((c for c in candidates if c in df.columns), None)
    if ts_col is None:
        raise ValueError(f"timestamp column not found in {candidates}")
    out = df.copy()
    out["ts"] = out[ts_col].apply(parse_ts_any)
    out = out.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    return out

def rolling_sum_numpy(x: np.ndarray, n: int) -> np.ndarray:
    if n <= 1:
        return x.astype(float)
    c = np.cumsum(np.nan_to_num(x, nan=0.0))
    out = c.copy()
    out[n:] = c[n:] - c[:-n]
    return out

def c(level: int, side: str, kind: str) -> str:
    # side in {"ask","bid"}, kind in {"px","qty"}
    if side=="ask" and kind=="px":  return f"最良売気配値{level}"
    if side=="ask" and kind=="qty": return f"最良売気配数量{level}"
    if side=="bid" and kind=="px":  return f"最良買気配値{level}"
    if side=="bid" and kind=="qty": return f"最良買気配数量{level}"
    raise ValueError("invalid side/kind")

def compute_features_ms2(df: pd.DataFrame, roll_n: int=20, k_depth: int=5) -> pd.DataFrame:
    df = ensure_ts(df)

    ask_px  = df[c(1,"ask","px")]
    bid_px  = df[c(1,"bid","px")]
    ask_qty = df[c(1,"ask","qty")]
    bid_qty = df[c(1,"bid","qty")]

    out = pd.DataFrame()
    out["ts"] = df["ts"]
    out["symbol"] = df["銘柄コード"] if "銘柄コード" in df.columns else ""

    out["spread"] = ask_px - bid_px
    out["mid"] = (ask_px + bid_px) / 2.0
    out["qi_l1"] = (bid_qty - ask_qty) / (bid_qty + ask_qty).replace(0, np.nan)

    denom = (bid_qty + ask_qty).replace(0, np.nan)
    micro = (ask_px*bid_qty + bid_px*ask_qty) / denom
    out["microprice"] = micro
    out["micro_bias"] = micro - out["mid"]

    d_bid_px = bid_px.diff().fillna(0)
    d_ask_px = ask_px.diff().fillna(0)
    d_bid_sz = bid_qty.diff().fillna(0)
    d_ask_sz = ask_qty.diff().fillna(0)
    ofi = ((d_bid_px > 0) * bid_qty + (d_bid_px == 0) * d_bid_sz) \
        - ((d_ask_px < 0) * ask_qty + (d_ask_px == 0) * d_ask_sz)
    out[f"ofi_{roll_n}"] = rolling_sum_numpy(ofi.values.astype(float), roll_n)

    def depth_sum(prefix: str) -> pd.Series:
        s = None
        for i in range(1, k_depth+1):
            col = c(i, prefix, "qty")
            if col in df.columns:
                s = df[col] if s is None else s.add(df[col], fill_value=0)
        return s if s is not None else pd.Series([np.nan]*len(df))
    bid_depth = depth_sum("bid")
    ask_depth = depth_sum("ask")
    out[f"depth_imb_{k_depth}"] = bid_depth - ask_depth

    return out

def main():
    import sys
    import traceback
    
    try:
        ap = argparse.ArgumentParser()
        ap.add_argument("--rss", required=True, help="MS2 RSS CSV (raw)")
        ap.add_argument("--out", required=True, help="output features CSV")
        ap.add_argument("--roll-n", type=int, default=20)
        ap.add_argument("--k-depth", type=int, default=5)
        args = ap.parse_args()

        print(f"Reading: {args.rss}", flush=True)
        df = read_csv_any(args.rss)
        print(f"Loaded {len(df)} rows", flush=True)
        
        print("Computing features...", flush=True)
        feats = compute_features_ms2(df, roll_n=args.roll_n, k_depth=args.k_depth)
        print(f"Generated {len(feats)} feature rows", flush=True)
        
        print(f"Writing to: {args.out}", flush=True)
        feats.to_csv(args.out, index=False)
        print(f"wrote: {args.out} rows={len(feats)}", flush=True)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
