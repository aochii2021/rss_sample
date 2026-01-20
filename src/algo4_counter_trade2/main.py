#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
逆張りアルゴ統合実行スクリプト
Phase別に処理を実行
"""
import argparse
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd: list):
    """コマンド実行"""
    print(f"\n>>> Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        print(f"ERROR: Command failed with code {result.returncode}")
        sys.exit(1)

def phase1_lob_features(rss_path: str, out_dir: str, roll_n: int, k_depth: int):
    """Phase 1.1: LOB特徴量計算"""
    print("\n=== Phase 1.1: LOB Features ===")
    out_path = os.path.join(out_dir, "lob_features.csv")
    run_cmd([
        sys.executable, "lob_features.py",
        "--rss", rss_path,
        "--out", out_path,
        "--roll-n", str(roll_n),
        "--k-depth", str(k_depth)
    ])
    return out_path

def phase1_ohlc(rss_path: str, out_dir: str, freq: str):
    """Phase 1.2: OHLC生成"""
    print("\n=== Phase 1.2: OHLC Generation ===")
    out_path = os.path.join(out_dir, f"ohlc_{freq}.csv")
    run_cmd([
        sys.executable, "ohlc_from_rss.py",
        "--rss", rss_path,
        "--out", out_path,
        "--freq", freq
    ])
    return out_path

def phase2_levels(ohlc_path: str, out_dir: str, bin_size: float, 
                  lookback: int, pivot_l: int, pivot_r: int):
    """Phase 2: サポレジ抽出"""
    print("\n=== Phase 2: Support/Resistance Levels ===")
    out_path = os.path.join(out_dir, "levels.jsonl")
    run_cmd([
        sys.executable, "sr_levels.py",
        "--min1", ohlc_path,
        "--out", out_path,
        "--bin-size", str(bin_size),
        "--lookback-bars", str(lookback),
        "--pivot-left", str(pivot_l),
        "--pivot-right", str(pivot_r)
    ])
    return out_path

def phase3_viz(rss_path: str, ohlc_path: str, levels_path: str, out_dir: str):
    """Phase 3: 可視化（銘柄別）"""
    print("\n=== Phase 3: Visualization ===")
    
    fig_dir = os.path.join(out_dir, "figs")
    os.makedirs(fig_dir, exist_ok=True)
    
    # LOB timeline（全銘柄）
    run_cmd([
        sys.executable, "viz_quicklook.py", "lob",
        "--lob", rss_path,
        "--out-dir", fig_dir
    ])
    
    # OHLC + levels（全銘柄）
    run_cmd([
        sys.executable, "viz_quicklook.py", "ohlc",
        "--ohlc", ohlc_path,
        "--levels", levels_path,
        "--out-dir", fig_dir
    ])
    
    return fig_dir

def phase4_backtest(lob_features_path: str, levels_path: str, out_dir: str,
                    k_tick: float, x_tick: float, y_tick: float,
                    max_hold: int, strength_th: float, roll_n: int, k_depth: int):
    """Phase 4: バックテスト"""
    print("\n=== Phase 4: Backtest ===")
    
    trades_path = os.path.join(out_dir, "trades.csv")
    summary_path = os.path.join(out_dir, "backtest_summary.json")
    
    run_cmd([
        sys.executable, "backtest_mean_reversion.py",
        "--lob-features", lob_features_path,
        "--levels", levels_path,
        "--out-trades", trades_path,
        "--out-summary", summary_path,
        "--k-tick", str(k_tick),
        "--x-tick", str(x_tick),
        "--y-tick", str(y_tick),
        "--max-hold-bars", str(max_hold),
        "--strength-threshold", str(strength_th),
        "--roll-n", str(roll_n),
        "--k-depth", str(k_depth)
    ])
    
    return trades_path, summary_path

def phase0_merge_data(input_dir: str, output_path: str):
    """Phase 0: データ結合（複数日のマーケットデータ）"""
    print("\n=== Phase 0: Merge Market Data ===")
    run_cmd([
        sys.executable, "merge_market_data.py",
        "--input-dir", input_dir,
        "--output", output_path
    ])
    return output_path

def main():
    ap = argparse.ArgumentParser(description="逆張りアルゴ統合実行")
    ap.add_argument("--rss", default="input/rss_market_data_merged.csv", help="MS2 RSS CSV")
    ap.add_argument("--market-order-book-dir", default="input/market_order_book",
                    help="マーケットデータの親ディレクトリ（日付別フォルダ）")
    ap.add_argument("--out-dir", default="output", help="output directory")
    ap.add_argument("--phase", choices=["all", "0", "1", "2", "3", "4"], default="all")
    ap.add_argument("--skip-merge", action="store_true", help="Phase 0（データ結合）をスキップ")
    
    # パラメータ
    ap.add_argument("--roll-n", type=int, default=20)
    ap.add_argument("--k-depth", type=int, default=5)
    ap.add_argument("--freq", default="1min", help="OHLC frequency")
    ap.add_argument("--bin-size", type=float, default=1.0)
    ap.add_argument("--lookback-bars", type=int, default=180)
    ap.add_argument("--pivot-left", type=int, default=3)
    ap.add_argument("--pivot-right", type=int, default=3)
    ap.add_argument("--k-tick", type=float, default=5.0)
    ap.add_argument("--x-tick", type=float, default=10.0)
    ap.add_argument("--y-tick", type=float, default=5.0)
    ap.add_argument("--max-hold-bars", type=int, default=60)
    ap.add_argument("--strength-threshold", type=float, default=0.5)
    
    args = ap.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)
    
    rss_path = os.path.join(SCRIPT_DIR, args.rss)
    
    # Phase 0: データ結合（スキップしない場合のみ）
    if not args.skip_merge and (args.phase in ["all", "0"]):
        market_dir = os.path.join(SCRIPT_DIR, args.market_order_book_dir)
        if os.path.exists(market_dir):
            rss_path = phase0_merge_data(market_dir, rss_path)
        else:
            print(f"WARNING: {market_dir} が見つかりません。データ結合をスキップします。")
    
    lob_features_path = None
    ohlc_path = None
    levels_path = None
    
    if args.phase in ["all", "1"]:
        lob_features_path = phase1_lob_features(rss_path, args.out_dir, args.roll_n, args.k_depth)
        ohlc_path = phase1_ohlc(rss_path, args.out_dir, args.freq)
    
    if args.phase in ["all", "2"]:
        if ohlc_path is None:
            ohlc_path = os.path.join(args.out_dir, f"ohlc_{args.freq}.csv")
        levels_path = phase2_levels(ohlc_path, args.out_dir, args.bin_size,
                                     args.lookback_bars, args.pivot_left, args.pivot_right)
    
    if args.phase in ["all", "3"]:
        if ohlc_path is None:
            ohlc_path = os.path.join(args.out_dir, f"ohlc_{args.freq}.csv")
        if levels_path is None:
            levels_path = os.path.join(args.out_dir, "levels.jsonl")
        phase3_viz(rss_path, ohlc_path, levels_path, args.out_dir)
    
    if args.phase in ["all", "4"]:
        if lob_features_path is None:
            lob_features_path = os.path.join(args.out_dir, "lob_features.csv")
        if levels_path is None:
            levels_path = os.path.join(args.out_dir, "levels.jsonl")
        phase4_backtest(lob_features_path, levels_path, args.out_dir,
                       args.k_tick, args.x_tick, args.y_tick,
                       args.max_hold_bars, args.strength_threshold,
                       args.roll_n, args.k_depth)
    
    print("\n=== All phases completed successfully! ===")

if __name__ == "__main__":
    main()
