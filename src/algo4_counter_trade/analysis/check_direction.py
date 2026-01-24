#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd

trades = pd.read_csv('output/trades_filtered.csv')

print("=" * 60)
print("【トレード方向の内訳】")
print("=" * 60)
print("\n総トレード数:", len(trades))
print("\n方向別:")
print(trades['direction'].value_counts())

buy_trades = trades[trades['direction'] == 'buy']
sell_trades = trades[trades['direction'] == 'sell']

print("\n" + "=" * 60)
print("【方向別パフォーマンス】")
print("=" * 60)

print("\n買いトレード:")
print(f"  トレード数: {len(buy_trades)}")
print(f"  総PnL: {buy_trades['pnl_tick'].sum():.1f} tick")
print(f"  勝率: {(buy_trades['pnl_tick'] > 0).mean() * 100:.1f}%")
print(f"  平均PnL: {buy_trades['pnl_tick'].mean():.2f} tick")

print("\n売りトレード:")
print(f"  トレード数: {len(sell_trades)}")
print(f"  総PnL: {sell_trades['pnl_tick'].sum():.1f} tick")
print(f"  勝率: {(sell_trades['pnl_tick'] > 0).mean() * 100:.1f}%")
print(f"  平均PnL: {sell_trades['pnl_tick'].mean():.2f} tick")

print("\n" + "=" * 60)
print("【銘柄別の方向分布】")
print("=" * 60)
for symbol in sorted(trades['symbol'].unique()):
    sym_trades = trades[trades['symbol'] == symbol]
    buy_count = (sym_trades['direction'] == 'buy').sum()
    sell_count = (sym_trades['direction'] == 'sell').sum()
    print(f"{symbol:8s}: 買い {buy_count:2d}  売り {sell_count:2d}")
