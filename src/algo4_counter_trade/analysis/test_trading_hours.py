#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""営業時間フィルタのテスト"""
import json
import pandas as pd

# 最適化前の結果
print("=" * 60)
print("【最適化前（全時間帯）】")
trades_all = pd.read_csv("output/trades.csv")
print(f"トレード数: {len(trades_all)}")
print(f"総PnL: {trades_all['pnl_tick'].sum():.1f} tick")
print(f"勝率: {(trades_all['pnl_tick']>0).mean()*100:.1f}%")

# 営業時間フィルタ後
print("\n" + "=" * 60)
print("【営業時間フィルタ後（9:00-15:00）】")
trades_filtered = pd.read_csv("output/trades_filtered.csv")
print(f"トレード数: {len(trades_filtered)}")
print(f"総PnL: {trades_filtered['pnl_tick'].sum():.1f} tick")
print(f"勝率: {(trades_filtered['pnl_tick']>0).mean()*100:.1f}%")

# 最適化パラメータ
print("\n" + "=" * 60)
print("【最適化パラメータ】")
with open("output/optimized_params_all.json") as f:
    params = json.load(f)
    for symbol, data in params.items():
        bp = data["best_params"]
        bm = data["best_metrics"]
        print(f"\n{symbol}:")
        print(f"  PnL: {bm['total_pnl']:+.1f} tick, 勝率: {bm['win_rate']*100:.1f}%, トレード数: {bm['num_trades']}")
        print(f"  k_tick={bp['k_tick']}, x_tick={bp['x_tick']}, y_tick={bp['y_tick']}, max_hold_bars={bp['max_hold_bars']}")
