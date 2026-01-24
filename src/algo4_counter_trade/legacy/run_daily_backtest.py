#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日別バックテスト：各取引日のレベルは前日までのチャートデータから生成
データリークを完全に防止
"""
import subprocess
import sys
import os
import pandas as pd
import json
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd: list):
    """コマンド実行"""
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        print(f"ERROR: Command failed with code {result.returncode}")
        sys.exit(1)

def main():
    print("=== 日別バックテスト（データリーク防止版） ===\n")
    
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
    
    # LOBデータから取引日を抽出
    lob_df = pd.read_csv("output/lob_features.csv")
    lob_df['ts'] = pd.to_datetime(lob_df['ts'])
    lob_df['date'] = lob_df['ts'].dt.date
    trading_dates = sorted(lob_df['date'].unique())
    
    print(f"\n検出された取引日: {len(trading_dates)}日")
    for td in trading_dates:
        print(f"  - {td}")
    
    all_trades = []
    
    # 日別にレベル生成 & バックテスト
    for i, trade_date in enumerate(trading_dates):
        print(f"\n{'='*60}")
        print(f"取引日 {i+1}/{len(trading_dates)}: {trade_date}")
        print(f"{'='*60}")
        
        # 前日までのデータを使用（その日のデータは除外）
        exclude_date = trade_date.strftime('%Y-%m-%d')
        print(f"チャートデータ除外: {exclude_date}以降")
        
        # Step 2: 揉み合いサポートライン生成（その日より前のデータのみ）
        levels_path = f"output/levels_{trade_date.strftime('%Y%m%d')}.jsonl"
        print(f"\nStep 2: サポートライン生成 → {levels_path}")
        run_cmd([
            sys.executable, "sr_levels.py",
            "--min1", "output/ohlc_1min.csv",
            "--chart-dir", "input/chart_data",
            "--out", levels_path,
            "--exclude-date-after", exclude_date
        ])
        
        # Step 3: その日のバックテスト実行
        trades_path = f"output/trades_{trade_date.strftime('%Y%m%d')}.csv"
        summary_path = f"output/backtest_{trade_date.strftime('%Y%m%d')}.json"
        print(f"\nStep 3: バックテスト実行（{trade_date}のみ）")
        
        # その日のLOBデータのみ抽出
        lob_day_path = f"output/lob_features_{trade_date.strftime('%Y%m%d')}.csv"
        lob_day = lob_df[lob_df['date'] == trade_date].copy()
        lob_day.to_csv(lob_day_path, index=False)
        print(f"  LOBデータ: {len(lob_day)}行")
        
        run_cmd([
            sys.executable, "backtest_mean_reversion.py",
            "--lob-features", lob_day_path,
            "--levels", levels_path,
            "--out-trades", trades_path,
            "--out-summary", summary_path
        ])
        
        # トレード結果を集約
        if os.path.exists(trades_path):
            df_trades = pd.read_csv(trades_path)
            if not df_trades.empty:
                all_trades.append(df_trades)
                print(f"  トレード数: {len(df_trades)}件")
    
    # 全日のトレードを結合
    if all_trades:
        print(f"\n{'='*60}")
        print("全期間の結果を統合")
        print(f"{'='*60}")
        
        combined_trades = pd.concat(all_trades, ignore_index=True)
        combined_trades.to_csv("output/trades_daily_combined.csv", index=False)
        
        # サマリー計算
        total = len(combined_trades)
        wins = len(combined_trades[combined_trades["pnl_tick"] > 0])
        losses = len(combined_trades[combined_trades["pnl_tick"] < 0])
        win_rate = wins / total if total > 0 else 0.0
        avg_pnl = combined_trades["pnl_tick"].mean()
        total_pnl = combined_trades["pnl_tick"].sum()
        
        summary = {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "avg_pnl_tick": avg_pnl,
            "total_pnl_tick": total_pnl,
            "trading_dates": len(trading_dates)
        }
        
        with open("output/backtest_daily_combined.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n=== 統合結果 ===")
        print(f"取引日数: {len(trading_dates)}日")
        print(f"総トレード数: {total}件")
        print(f"勝ち: {wins}件 / 負け: {losses}件")
        print(f"勝率: {win_rate*100:.1f}%")
        print(f"平均損益: {avg_pnl:.2f} tick")
        print(f"総損益: {total_pnl:.2f} tick")
        print(f"\n保存先:")
        print(f"  - output/trades_daily_combined.csv")
        print(f"  - output/backtest_daily_combined.json")
    else:
        print("\nトレードがありませんでした。")

if __name__ == "__main__":
    main()
