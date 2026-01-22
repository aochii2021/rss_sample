#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""全バックテスト結果比較"""
import json

print("=== バックテスト結果比較 ===\n")

# 通常版（全レベル）
print("■ 通常版（全S/Rレベル使用）")
s_all = json.load(open('output/backtest_daily_combined.json'))
print(f"  総トレード数: {s_all['total_trades']}件")
print(f"  勝率: {s_all['win_rate']*100:.1f}%")
print(f"  総損益: {s_all['total_pnl_tick']:.2f} tick")
print(f"  平均損益: {s_all['avg_pnl_tick']:.2f} tick")

# 過去3営業日分足揉み合いのみ
print("\n■ 過去3営業日分足揉み合いのみ + 日足補完")
s_3d = json.load(open('output/backtest_3d_combined.json'))
print(f"  総トレード数: {s_3d['total_trades']}件")
print(f"  勝率: {s_3d['win_rate']*100:.1f}%")
print(f"  総損益: {s_3d['total_pnl_tick']:.2f} tick")
print(f"  平均損益: {s_3d['avg_pnl_tick']:.2f} tick")

print("\n=== 日別内訳（3営業日分足版） ===\n")
s19 = json.load(open('output/backtest_3d_20260119.json'))
s20 = json.load(open('output/backtest_3d_20260120.json'))

print(f"■ 2026-01-19")
print(f"  トレード数: {s19['total_trades']}件")
print(f"  勝率: {s19['win_rate']*100:.1f}%")
print(f"  総損益: {s19['total_pnl_tick']:.1f} tick")
print(f"  平均損益: {s19['avg_pnl_tick']:.2f} tick")

print(f"\n■ 2026-01-20")
print(f"  トレード数: {s20['total_trades']}件")
print(f"  勝率: {s20['win_rate']*100:.1f}%")
print(f"  総損益: {s20['total_pnl_tick']:.1f} tick")
print(f"  平均損益: {s20['avg_pnl_tick']:.2f} tick")

print("\n=== 比較 ===")
print(f"トレード数削減: {s_all['total_trades']}件 → {s_3d['total_trades']}件 ({s_3d['total_trades']/s_all['total_trades']*100:.1f}%)")
print(f"総損益変化: {s_all['total_pnl_tick']:.1f} tick → {s_3d['total_pnl_tick']:.1f} tick ({s_3d['total_pnl_tick'] - s_all['total_pnl_tick']:+.1f})")
print(f"平均損益: {s_all['avg_pnl_tick']:.2f} tick → {s_3d['avg_pnl_tick']:.2f} tick ({s_3d['avg_pnl_tick'] - s_all['avg_pnl_tick']:+.2f})")
