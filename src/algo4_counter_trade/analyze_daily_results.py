#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""日別パフォーマンス比較"""
import json
import pandas as pd

print("=== 日別パフォーマンス比較 ===\n")

dates = ['20260119', '20260120']
for date in dates:
    print(f"■ {date[:4]}-{date[4:6]}-{date[6:]}")
    summary = json.load(open(f'output/backtest_{date}.json'))
    print(f"  トレード数: {summary['total_trades']}件")
    print(f"  勝率: {summary['win_rate']*100:.1f}%")
    print(f"  総損益: {summary['total_pnl_tick']:.2f} tick")
    print(f"  平均損益: {summary['avg_pnl_tick']:.2f} tick")
    print()

print("=== 統合結果 ===")
summary_total = json.load(open('output/backtest_daily_combined.json'))
print(f"取引日数: {summary_total['trading_dates']}日")
print(f"総トレード数: {summary_total['total_trades']}件")
print(f"勝率: {summary_total['win_rate']*100:.1f}%")
print(f"総損益: {summary_total['total_pnl_tick']:.2f} tick")
print(f"平均損益: {summary_total['avg_pnl_tick']:.2f} tick")
