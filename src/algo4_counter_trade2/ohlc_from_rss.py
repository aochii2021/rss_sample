#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MS2 RSS CSVから分足OHLCを生成します。
"""
import argparse
import logging
import sys
from datetime import datetime
import numpy as np
import pandas as pd

import validation

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

ENCODINGS = ["utf-8-sig", "utf-8", "cp932", "utf-16"]

def read_csv_any(path: str) -> pd.DataFrame:
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path)

def parse_ts_any(x):
    if pd.isna(x) or str(x).strip() in ("", "  :  ", "  :  :  "):
        return pd.NaT
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(str(x).strip(), fmt)
        except Exception:
            pass
    return pd.to_datetime(x, errors="coerce")

def create_ohlc(df: pd.DataFrame, freq: str = "1min") -> pd.DataFrame:
    """
    MS2 RSSデータから分足OHLCを生成
    freq: '1min', '5min', '1h', '1D' など
    """
    # 時刻列の選択（優先順）
    ts_col = None
    for c in ("記録日時", "現在値詳細時刻", "現在値時刻"):
        if c in df.columns:
            ts_col = c
            break
    if ts_col is None:
        raise ValueError("timestamp column not found")
    
    # 時刻パース
    df = df.copy()
    df["ts"] = df[ts_col].apply(parse_ts_any)
    df = df.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    
    # Mid価格を終値として使用（最良気配の中値）
    ask_col = "最良売気配値1" if "最良売気配値1" in df.columns else "最良売気配値"
    bid_col = "最良買気配値1" if "最良買気配値1" in df.columns else "最良買気配値"
    
    if ask_col not in df.columns or bid_col not in df.columns:
        raise ValueError(f"ask/bid columns not found: {ask_col}, {bid_col}")
    
    df["price"] = (df[ask_col] + df[bid_col]) / 2.0
    df = df.dropna(subset=["price"])
    
    # 出来高（存在しない場合は0）
    df["volume"] = df["出来高"] if "出来高" in df.columns else 0
    
    # 銘柄コード
    symbol_col = "銘柄コード" if "銘柄コード" in df.columns else None
    
    # リサンプリング
    df.set_index("ts", inplace=True)
    
    if symbol_col and symbol_col in df.columns:
        # 銘柄別にグループ化
        ohlc_list = []
        for symbol, group in df.groupby(symbol_col):
            if pd.isna(symbol) or symbol == "":
                continue
            resampled = group["price"].resample(freq).ohlc()
            resampled["volume"] = group["volume"].resample(freq).sum()
            resampled["symbol"] = symbol
            ohlc_list.append(resampled)
        
        if ohlc_list:
            ohlc = pd.concat(ohlc_list).reset_index()
        else:
            # 銘柄なしでも続行
            ohlc = df["price"].resample(freq).ohlc()
            ohlc["volume"] = df["volume"].resample(freq).sum()
            ohlc = ohlc.reset_index()
    else:
        ohlc = df["price"].resample(freq).ohlc()
        ohlc["volume"] = df["volume"].resample(freq).sum()
        ohlc = ohlc.reset_index()
    
    # 列名統一
    ohlc.rename(columns={"ts": "timestamp"}, inplace=True)
    
    # 欠損除外
    ohlc = ohlc.dropna(subset=["open", "high", "low", "close"])
    
    return ohlc

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rss", required=True, help="MS2 RSS CSV")
    ap.add_argument("--out", required=True, help="output OHLC CSV")
    ap.add_argument("--freq", default="1min", help="resample frequency (default: 1min)")
    args = ap.parse_args()
    
    try:
        # ファイル存在確認
        validation.validate_file_exists(args.rss)
        
        # 出力ディレクトリ確保
        validation.ensure_output_directory(args.out)
        
        df = read_csv_any(args.rss)
        logger.info(f"Loaded RSS data: {len(df)} rows")
        
        ohlc = create_ohlc(df, freq=args.freq)
        logger.info(f"Generated OHLC: {len(ohlc)} rows")
        
        # 価格異常検出
        anomalies = validation.detect_price_anomaly(ohlc, col="close")
        if not anomalies.empty:
            logger.warning(f"Found {len(anomalies)} price anomalies")
        
        ohlc.to_csv(args.out, index=False)
        logger.info(f"Wrote: {args.out}")
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(2)

if __name__ == "__main__":
    main()
