#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
営業時間フィルタ適用後のバックテスト結果サマリー
"""
import json
import pandas as pd

print("=" * 70)
print("【営業時間フィルタ適用後の最適化結果】")
print("売買時間: 9:00 - 15:00")
print("=" * 70)

# 最適化結果の読み込み
with open('output/optimized_params_trading_hours.json') as f:
    params = json.load(f)

# トレード結果の読み込み
trades = pd.read_csv('output/trades_filtered.csv')

# 銘柄別サマリー
print("\n【銘柄別パフォーマンス】\n")
total_pnl = 0
for symbol in sorted(params.keys()):
    data = params[symbol]
    metrics = data['best_metrics']
    bp = data['best_params']
    
    pnl = metrics['total_pnl']
    total_pnl += pnl
    
    print(f"{symbol:8s}  PnL: {pnl:+7.1f} tick  勝率: {metrics['win_rate']*100:5.1f}%  "
          f"トレード: {metrics['num_trades']:3d}  TO率: {metrics['timeout_rate']*100:5.1f}%")
    print(f"         k_tick={bp['k_tick']:.1f}, x_tick={bp['x_tick']:.1f}, "
          f"y_tick={bp['y_tick']:.1f}, max_hold_bars={bp['max_hold_bars']}")
    print()

print("-" * 70)
print(f"合計PnL: {total_pnl:+.1f} tick")
print("=" * 70)

# 全体統計
print("\n【全体統計】\n")
print(f"総トレード数: {len(trades)}")
print(f"勝ちトレード: {(trades['pnl_tick'] > 0).sum()}")
print(f"負けトレード: {(trades['pnl_tick'] < 0).sum()}")
print(f"全体勝率: {(trades['pnl_tick'] > 0).mean() * 100:.1f}%")
print(f"平均PnL: {trades['pnl_tick'].mean():.2f} tick")
print(f"平均保有時間: {trades['hold_bars'].mean():.1f} バー")
print(f"タイムアウト率: {(trades['exit_reason'] == 'TO').mean() * 100:.1f}%")

print("\n可視化ファイル:")
print("- output/figs/ohlc_levels_*.png (トレードポイント付き)")
print("\n設定ファイル:")
print("- config.py (SYMBOL_PARAMS に最適化結果を反映)")
print("=" * 70)
