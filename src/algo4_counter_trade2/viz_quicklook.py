#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LOBタイムライン・OHLC+レベル線の可視化
"""
import argparse
import json
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

plt.rcParams["font.sans-serif"] = ["Yu Gothic", "MS Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

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

def ensure_ts(df: pd.DataFrame) -> pd.DataFrame:
    candidates = ("記録日時", "現在値詳細時刻", "現在値時刻")
    ts_col = next((c for c in candidates if c in df.columns), None)
    if ts_col is None:
        raise ValueError(f"timestamp column not found in {candidates}")
    
    out = df.copy()
    out["ts"] = out[ts_col].apply(parse_ts_any)
    out = out.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    return out

def viz_lob_timeline(lob_path: str, out_dir: str, symbol: str = None):
    """LOB mid/spreadのタイムライン表示（銘柄別）"""
    df = read_csv_any(lob_path)
    df = ensure_ts(df)
    
    ask_col = "最良売気配値1" if "最良売気配値1" in df.columns else "最良売気配値"
    bid_col = "最良買気配値1" if "最良買気配値1" in df.columns else "最良買気配値"
    
    # 銘柄列を特定
    symbol_col = None
    for col in ["symbol", "銘柄コード"]:
        if col in df.columns:
            symbol_col = col
            break
    
    if symbol_col and symbol:
        df = df[df[symbol_col] == symbol].copy()
        if df.empty:
            print(f"No data for symbol={symbol}, skipping.")
            return
    
    mid = (df[ask_col] + df[bid_col]) / 2.0
    spread = df[ask_col] - df[bid_col]
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    
    axes[0].plot(df["ts"], mid, linewidth=0.8)
    axes[0].set_ylabel("Mid Price")
    title_prefix = f"[{symbol}] " if symbol else ""
    axes[0].set_title(f"{title_prefix}LOB Mid Price Timeline")
    axes[0].grid(alpha=0.3)
    
    axes[1].plot(df["ts"], spread, linewidth=0.8, color="orange")
    axes[1].set_ylabel("Spread")
    axes[1].set_xlabel("Time")
    axes[1].set_title(f"{title_prefix}Spread Timeline")
    axes[1].grid(alpha=0.3)
    
    plt.tight_layout()
    
    # 出力ファイル名に銘柄を含める
    import os
    os.makedirs(out_dir, exist_ok=True)
    filename = f"lob_timeline_{symbol}.png" if symbol else "lob_timeline.png"
    out_path = os.path.join(out_dir, filename)
    plt.savefig(out_path, dpi=150)
    print(f"saved: {out_path}")
    plt.close()

def viz_ohlc_levels(ohlc_path: str, levels_path: str, out_dir: str, symbol: str = None, trades_path: str = None):
    """OHLC + S/Rレベル線 + トレードポイントの表示（銘柄別）"""
    df = pd.read_csv(ohlc_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    # 銘柄フィルタ
    if symbol and "symbol" in df.columns:
        df = df[df["symbol"] == symbol].copy()
        if df.empty:
            print(f"No OHLC data for symbol={symbol}, skipping.")
            return
    
    with open(levels_path, "r", encoding="utf-8") as f:
        levels = [json.loads(line) for line in f]
    
    # レベルも銘柄でフィルタ
    if symbol:
        levels = [lv for lv in levels if lv.get("symbol") == symbol]
    
    # トレードデータ読み込み
    trades = None
    if trades_path:
        trades = pd.read_csv(trades_path)
        if "entry_ts" in trades.columns:
            trades["entry_ts"] = pd.to_datetime(trades["entry_ts"])
        if "exit_ts" in trades.columns:
            trades["exit_ts"] = pd.to_datetime(trades["exit_ts"])
        if symbol and "symbol" in trades.columns:
            trades = trades[trades["symbol"] == symbol].copy()
    
    fig, ax = plt.subplots(figsize=(14, 7))
    
    ax.plot(df["timestamp"], df["close"], linewidth=1, label="Close", color="navy", zorder=1)
    
    # レベル線描画
    colors = {
        "recent_high": "red",
        "recent_low": "green",
        "vpoc": "purple",
        "hvn": "magenta",
        "swing_resistance": "darkred",
        "swing_support": "darkgreen",
        "prev_high": "orange",
        "prev_low": "cyan",
        "prev_close": "gray"
    }
    
    for lv in levels:
        kind = lv["kind"]
        level_now = lv["level_now"]
        strength = lv.get("strength", 0.5)
        
        color = colors.get(kind, "black")
        alpha = 0.3 + 0.6 * strength
        linewidth = 0.5 + 1.5 * strength
        
        ax.axhline(level_now, color=color, linestyle="--", linewidth=linewidth, 
                   alpha=alpha, label=f"{kind} ({level_now:.1f})")
    
    # トレードポイントをプロット
    if trades is not None and not trades.empty:
        # エントリーとエグジットを線で結ぶ（対応関係を明確化）
        for _, trade in trades.iterrows():
            # 買いトレードは緑系、売りトレードは赤系
            if trade["direction"] == "buy":
                line_color = "green"
                entry_marker_color = "limegreen"
                entry_edge_color = "darkgreen"
            else:
                line_color = "red"
                entry_marker_color = "orangered"
                entry_edge_color = "darkred"
            
            # 利確は実線、損切は破線
            if trade["pnl_tick"] > 0:
                linestyle = "-"
                exit_marker_color = "gold"
                exit_edge_color = "orange"
            else:
                linestyle = "--"
                exit_marker_color = "silver"
                exit_edge_color = "dimgray"
            
            # エントリー→エグジットを線で結ぶ
            ax.plot([trade["entry_ts"], trade["exit_ts"]], 
                   [trade["entry_price"], trade["exit_price"]], 
                   color=line_color, linestyle=linestyle, linewidth=1.5, 
                   alpha=0.4, zorder=3)
        
        # 買いエントリー（緑の上向き三角）
        buy_entries = trades[trades["direction"] == "buy"]
        if not buy_entries.empty:
            ax.scatter(buy_entries["entry_ts"], buy_entries["entry_price"], 
                      marker="^", s=120, color="limegreen", edgecolors="darkgreen",
                      label="Entry (Buy)", zorder=5, alpha=0.9, linewidths=1.5)
        
        # 売りエントリー（赤の下向き三角）
        sell_entries = trades[trades["direction"] == "sell"]
        if not sell_entries.empty:
            ax.scatter(sell_entries["entry_ts"], sell_entries["entry_price"], 
                      marker="v", s=120, color="orangered", edgecolors="darkred",
                      label="Entry (Sell)", zorder=5, alpha=0.9, linewidths=1.5)
        
        # エグジットポイント（円形、利確=金色、損切=グレー）
        wins = trades[trades["pnl_tick"] > 0]
        losses = trades[trades["pnl_tick"] <= 0]
        
        if not wins.empty:
            ax.scatter(wins["exit_ts"], wins["exit_price"],
                      marker="o", s=80, color="gold", edgecolors="orange",
                      label="Exit (Profit)", zorder=5, alpha=0.8, linewidths=1.5)
        
        if not losses.empty:
            ax.scatter(losses["exit_ts"], losses["exit_price"],
                      marker="o", s=80, color="silver", edgecolors="dimgray",
                      label="Exit (Loss)", zorder=5, alpha=0.8, linewidths=1.5)
    
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    title_prefix = f"[{symbol}] " if symbol else ""
    trade_info = f" ({len(trades)} trades)" if trades is not None and not trades.empty else ""
    ax.set_title(f"{title_prefix}OHLC + S/R Levels + Trade Points{trade_info}")
    ax.grid(alpha=0.3)
    
    # 凡例（重複除外）
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="best", fontsize=7)
    
    plt.tight_layout()
    
    # 出力ファイル名に銘柄を含める
    import os
    os.makedirs(out_dir, exist_ok=True)
    filename = f"ohlc_levels_{symbol}.png" if symbol else "ohlc_levels.png"
    out_path = os.path.join(out_dir, filename)
    plt.savefig(out_path, dpi=150)
    print(f"saved: {out_path}")
    plt.close()

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    
    # LOB timeline
    p_lob = sub.add_parser("lob")
    p_lob.add_argument("--lob", required=True)
    p_lob.add_argument("--out-dir", required=True)
    p_lob.add_argument("--symbol", default=None, help="Symbol to filter (optional)")
    
    # OHLC + levels
    p_ohlc = sub.add_parser("ohlc")
    p_ohlc.add_argument("--ohlc", required=True)
    p_ohlc.add_argument("--levels", required=True)
    p_ohlc.add_argument("--out-dir", required=True)
    p_ohlc.add_argument("--symbol", default=None, help="Symbol to filter (optional)")
    p_ohlc.add_argument("--trades", default=None, help="Trades CSV to overlay (optional)")
    
    args = ap.parse_args()
    
    if args.cmd == "lob":
        if args.symbol:
            viz_lob_timeline(args.lob, args.out_dir, args.symbol)
        else:
            # 全銘柄を処理
            df = read_csv_any(args.lob)
            symbol_col = None
            for col in ["symbol", "銘柄コード"]:
                if col in df.columns:
                    symbol_col = col
                    break
            
            if symbol_col:
                symbols = df[symbol_col].unique()
                print(f"Processing {len(symbols)} symbols: {list(symbols)}")
                for sym in symbols:
                    viz_lob_timeline(args.lob, args.out_dir, sym)
            else:
                viz_lob_timeline(args.lob, args.out_dir)
    
    elif args.cmd == "ohlc":
        if args.symbol:
            viz_ohlc_levels(args.ohlc, args.levels, args.out_dir, args.symbol, args.trades)
        else:
            # 全銘柄を処理
            df = pd.read_csv(args.ohlc)
            if "symbol" in df.columns:
                symbols = df["symbol"].unique()
                print(f"Processing {len(symbols)} symbols: {list(symbols)}")
                for sym in symbols:
                    viz_ohlc_levels(args.ohlc, args.levels, args.out_dir, sym, args.trades)
            else:
                viz_ohlc_levels(args.ohlc, args.levels, args.out_dir, None, args.trades)
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
