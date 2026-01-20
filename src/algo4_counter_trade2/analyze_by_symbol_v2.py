#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""銘柄別損益分析（ファイル指定可能版）"""
import pandas as pd
import sys

def analyze_by_symbol(csv_path):
    df = pd.read_csv(csv_path)
    
    print(f"=== 銘柄別損益分析 ({csv_path}) ===\n")
    
    # 銘柄別に集計
    summary = df.groupby('symbol').agg({
        'pnl_tick': ['count', 'sum', 'mean'],
        'direction': lambda x: (x == 'buy').sum(),
        'exit_reason': lambda x: (x == 'TP').sum()
    }).round(2)
    
    summary.columns = ['トレード数', '総損益(tick)', '平均損益(tick)', '買いトレード数', 'TP数']
    
    # 勝率を計算
    for symbol in summary.index:
        symbol_trades = df[df['symbol'] == symbol]
        wins = (symbol_trades['pnl_tick'] > 0).sum()
        total = len(symbol_trades)
        win_rate = wins / total * 100 if total > 0 else 0
        summary.loc[symbol, '勝率(%)'] = round(win_rate, 1)
        
        # 売りトレード数
        sells = (symbol_trades['direction'] == 'sell').sum()
        summary.loc[symbol, '売りトレード数'] = sells
    
    # 並べ替え（総損益の降順）
    summary = summary.sort_values('総損益(tick)', ascending=False)
    
    print(summary[['トレード数', '総損益(tick)', '平均損益(tick)', '勝率(%)', '買いトレード数', '売りトレード数', 'TP数']])
    
    print("\n【詳細】")
    for symbol in summary.index:
        symbol_trades = df[df['symbol'] == symbol]
        print(f"\n■ {symbol}")
        print(f"  総損益: {summary.loc[symbol, '総損益(tick)']:.1f} tick")
        print(f"  トレード数: {int(summary.loc[symbol, 'トレード数'])}件 (買い: {int(summary.loc[symbol, '買いトレード数'])}, 売り: {int(summary.loc[symbol, '売りトレード数'])})")
        print(f"  勝率: {summary.loc[symbol, '勝率(%)']}%")
        print(f"  平均損益: {summary.loc[symbol, '平均損益(tick)']:.2f} tick")
        print(f"  TP達成: {int(summary.loc[symbol, 'TP数'])}回")
        
        # 最大利益/損失
        max_profit = symbol_trades['pnl_tick'].max()
        max_loss = symbol_trades['pnl_tick'].min()
        print(f"  最大利益: +{max_profit:.1f} tick, 最大損失: {max_loss:.1f} tick")
    
    print(f"\n【全体】")
    print(f"  総トレード数: {len(df)}件")
    print(f"  総損益: {df['pnl_tick'].sum():.1f} tick")
    print(f"  平均損益: {df['pnl_tick'].mean():.2f} tick")
    print(f"  全体勝率: {(df['pnl_tick'] > 0).sum() / len(df) * 100:.1f}%")

if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "output/trades_consolidation.csv"
    analyze_by_symbol(csv_path)
