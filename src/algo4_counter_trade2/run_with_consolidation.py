#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日足・分足データから揉み合いサポートラインを生成してバックテスト実行
"""
import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd: list):
    """コマンド実行"""
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        print(f"ERROR: Command failed with code {result.returncode}")
        sys.exit(1)

def main():
    print("=== 揉み合いサポートライン生成 & バックテスト ===\n")
    
    # Step 0: マーケットデータ結合
    print("Step 0: マーケットデータ結合")
    run_cmd([
        sys.executable, "merge_market_data.py",
        "--input-dir", "input/market_order_book",
        "--output", "input/rss_market_data_merged.csv"
    ])
    
    # Step 0.5: LOB特徴量とOHLC生成
    print("\nStep 0.5: LOB特徴量 & OHLC生成")
    run_cmd([
        sys.executable, "lob_features.py",
        "--rss", "input/rss_market_data_merged.csv",
        "--out", "output/lob_features.csv"
    ])
    run_cmd([
        sys.executable, "ohlc_from_rss.py",
        "--rss", "input/rss_market_data_merged.csv",
        "--out", "output/ohlc_1min.csv",
        "--freq", "1min"
    ])
    
    # Step 1: チャートデータをインポート
    print("\nStep 1: チャートデータインポート")
    run_cmd([sys.executable, "import_chart_data.py"])
    
    # Step 2: 揉み合いサポートライン生成（1月19日用：1月19日のデータを除外）
    print("\nStep 2: 揉み合いサポートライン生成（データリーク防止）")
    run_cmd([
        sys.executable, "sr_levels.py",
        "--min1", "output/ohlc_1min.csv",
        "--chart-dir", "input/chart_data",
        "--out", "output/levels_with_consolidation.jsonl",
        "--exclude-date-after", "2026-01-19"
    ])
    
    # Step 3: バックテスト実行
    print("\nStep 3: バックテスト実行")
    run_cmd([
        sys.executable, "backtest_mean_reversion.py",
        "--lob-features", "output/lob_features.csv",
        "--levels", "output/levels_with_consolidation.jsonl",
        "--out-trades", "output/trades_consolidation.csv",
        "--out-summary", "output/backtest_consolidation.json"
    ])
    
    # Step 4: 可視化
    print("\nStep 4: 可視化")
    run_cmd([
        sys.executable, "viz_quicklook.py", "ohlc",
        "--ohlc", "output/ohlc_1min.csv",
        "--levels", "output/levels_with_consolidation.jsonl",
        "--trades", "output/trades_consolidation.csv",
        "--out-dir", "output/figs"
    ])
    
    print("\n=== 完了 ===")
    print("結果:")
    print("  - マーケットデータ: input/rss_market_data_merged.csv")
    print("  - サポートライン: output/levels_with_consolidation.jsonl")
    print("  - トレード: output/trades_consolidation.csv")
    print("  - サマリー: output/backtest_consolidation.json")
    print("  - チャート: output/figs/")

if __name__ == "__main__":
    main()
