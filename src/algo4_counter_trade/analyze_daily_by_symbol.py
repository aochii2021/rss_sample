#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""日別・銘柄別パフォーマンス分析"""
import pandas as pd
import json

print("=== 日別・銘柄別パフォーマンス分析 ===\n")

dates = ['20260119', '20260120']

for date in dates:
    date_str = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    print(f"■ {date_str}")
    
    trades_path = f'output/trades_3d_{date}.csv'
    df = pd.read_csv(trades_path)
    
    if df.empty:
        print("  トレードなし\n")
        continue
    
    # 銘柄別集計
    summary = df.groupby('symbol').agg({
        'pnl_tick': ['count', 'sum', 'mean'],
        'exit_reason': lambda x: (x == 'TP').sum()
    }).round(2)
    
    summary.columns = ['トレード数', '総損益(tick)', '平均損益(tick)', 'TP数']
    
    # 勝率を計算
    for symbol in summary.index:
        symbol_trades = df[df['symbol'] == symbol]
        wins = (symbol_trades['pnl_tick'] > 0).sum()
        total = len(symbol_trades)
        win_rate = wins / total * 100 if total > 0 else 0
        summary.loc[symbol, '勝率(%)'] = round(win_rate, 1)
    
    summary = summary.sort_values('総損益(tick)', ascending=False)
    
    for symbol in summary.index:
        print(f"  {symbol}: {int(summary.loc[symbol, 'トレード数'])}件, "
              f"勝率{summary.loc[symbol, '勝率(%)']}%, "
              f"総損益{summary.loc[symbol, '総損益(tick)']:.1f} tick, "
              f"平均{summary.loc[symbol, '平均損益(tick)']:.2f} tick, "
              f"TP{int(summary.loc[symbol, 'TP数'])}回")
    
    # 日別合計
    total_trades = len(df)
    total_pnl = df['pnl_tick'].sum()
    avg_pnl = df['pnl_tick'].mean()
    wins = (df['pnl_tick'] > 0).sum()
    win_rate = wins / total_trades * 100
    tp_count = (df['exit_reason'] == 'TP').sum()
    
    print(f"  【日別合計】: {total_trades}件, 勝率{win_rate:.1f}%, "
          f"総損益{total_pnl:.1f} tick, 平均{avg_pnl:.2f} tick, TP{tp_count}回\n")

# 全体サマリー
print("=== 全期間サマリー（過去3営業日分足版） ===")
df_all = pd.read_csv('output/trades_3d_combined.csv')
print(f"総トレード数: {len(df_all)}件")
print(f"勝率: {(df_all['pnl_tick'] > 0).sum() / len(df_all) * 100:.1f}%")
print(f"総損益: {df_all['pnl_tick'].sum():.1f} tick")
print(f"平均損益: {df_all['pnl_tick'].mean():.2f} tick")
print(f"TP達成: {(df_all['exit_reason'] == 'TP').sum()}回")

# 銘柄別サマリー
print("\n銘柄別:")
for symbol in df_all['symbol'].unique():
    df_sym = df_all[df_all['symbol'] == symbol]
    print(f"  {symbol}: {len(df_sym)}件 (1/19: {len(df_sym[pd.to_datetime(df_sym['entry_ts']).dt.date == pd.to_datetime('2026-01-19').date()])}件, "
          f"1/20: {len(df_sym[pd.to_datetime(df_sym['entry_ts']).dt.date == pd.to_datetime('2026-01-20').date()])}件)")
