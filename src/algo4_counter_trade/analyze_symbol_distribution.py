"""
銘柄別分布チェック（壊れないか検証用）
- 銘柄別PF
- 銘柄別平均PnL
- トレード数集中度
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path

def analyze_symbol_distribution(run_dir: str):
    """銘柄別の分布を分析"""
    trades_path = Path(run_dir) / 'output' / 'trades.csv'
    
    if not trades_path.exists():
        print(f"❌ {trades_path} が見つかりません")
        return
    
    df = pd.read_csv(trades_path)
    
    print("=" * 70)
    print("📊 銘柄別分布チェック（v1.0 最終候補検証）")
    print("=" * 70)
    print()
    
    # 銘柄別集計
    symbol_stats = []
    for symbol in df['symbol'].unique():
        symbol_df = df[df['symbol'] == symbol]
        pnl = symbol_df['pnl_tick']
        
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        
        gross_profit = wins.sum() if len(wins) > 0 else 0
        gross_loss = -losses.sum() if len(losses) > 0 else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        symbol_stats.append({
            'symbol': symbol,
            'trades': len(pnl),
            'avg_pnl': pnl.mean(),
            'total_pnl': pnl.sum(),
            'pf': pf,
            'win_rate': len(wins) / len(pnl) if len(pnl) > 0 else 0,
            'avg_win': wins.mean() if len(wins) > 0 else 0,
            'avg_loss': losses.mean() if len(losses) > 0 else 0
        })
    
    stats_df = pd.DataFrame(symbol_stats).sort_values('trades', ascending=False)
    total_trades = len(df)
    
    # 1. トレード数集中度
    print("【1】トレード数集中度")
    print("-" * 70)
    print(f"総トレード数: {total_trades}本")
    print(f"銘柄数: {len(stats_df)}銘柄")
    print()
    
    top_10 = stats_df.head(10).copy()
    top_10['pct'] = (top_10['trades'] / total_trades * 100).round(1)
    
    print("📈 トレード数Top10:")
    for idx, row in top_10.iterrows():
        pf_status = "✅" if row['pf'] >= 1.0 else "⚠️"
        print(f"  {row['symbol']}: {row['trades']:3d}本 ({row['pct']:4.1f}%) "
              f"| PF={row['pf']:.2f} {pf_status} | 平均={row['avg_pnl']:+.2f}tick")
    
    print()
    top1_pct = (stats_df.iloc[0]['trades'] / total_trades * 100)
    top5_pct = (stats_df.head(5)['trades'].sum() / total_trades * 100)
    
    print(f"📊 集中度指標:")
    print(f"  Top1銘柄: {top1_pct:.1f}% {'✅' if top1_pct < 15 else '⚠️ 15%超'}")
    print(f"  Top5合計: {top5_pct:.1f}%")
    print()
    
    # 2. 銘柄別PF分布
    print("【2】銘柄別PF分布")
    print("-" * 70)
    
    # トレード数5本以上の銘柄に限定（統計的意味のあるもの）
    valid_symbols = stats_df[stats_df['trades'] >= 5].copy()
    
    pf_below_1 = valid_symbols[valid_symbols['pf'] < 1.0]
    pf_1_to_13 = valid_symbols[(valid_symbols['pf'] >= 1.0) & (valid_symbols['pf'] < 1.3)]
    pf_13_to_15 = valid_symbols[(valid_symbols['pf'] >= 1.3) & (valid_symbols['pf'] < 1.5)]
    pf_above_15 = valid_symbols[valid_symbols['pf'] >= 1.5]
    
    print(f"（トレード数5本以上の銘柄に限定: {len(valid_symbols)}銘柄）")
    print()
    print(f"  PF < 1.0    : {len(pf_below_1):2d}銘柄 ({len(pf_below_1)/len(valid_symbols)*100:4.1f}%)")
    print(f"  PF 1.0-1.3  : {len(pf_1_to_13):2d}銘柄 ({len(pf_1_to_13)/len(valid_symbols)*100:4.1f}%)")
    print(f"  PF 1.3-1.5  : {len(pf_13_to_15):2d}銘柄 ({len(pf_13_to_15)/len(valid_symbols)*100:4.1f}%)")
    print(f"  PF ≥ 1.5    : {len(pf_above_15):2d}銘柄 ({len(pf_above_15)/len(valid_symbols)*100:4.1f}%)")
    print()
    
    pf_below_1_pct = len(pf_below_1) / len(valid_symbols) * 100 if len(valid_symbols) > 0 else 0
    if pf_below_1_pct < 50:
        print(f"✅ 合格: PF<1の銘柄が過半数未満（{pf_below_1_pct:.1f}%）")
    else:
        print(f"⚠️ 注意: PF<1の銘柄が過半数超（{pf_below_1_pct:.1f}%）")
    print()
    
    # 3. PF最悪Top5
    print("【3】PF最悪Top5（トレード数5本以上）")
    print("-" * 70)
    worst_pf = valid_symbols.nsmallest(5, 'pf')
    for idx, row in worst_pf.iterrows():
        print(f"  {row['symbol']}: PF={row['pf']:.2f} | {row['trades']}本 | "
              f"平均={row['avg_pnl']:+.2f}tick | 勝率={row['win_rate']*100:.1f}%")
    print()
    
    # 4. PF優良Top5
    print("【4】PF優良Top5（トレード数5本以上）")
    print("-" * 70)
    best_pf = valid_symbols.nlargest(5, 'pf')
    for idx, row in best_pf.iterrows():
        pf_display = f"{row['pf']:.2f}" if row['pf'] < 99 else "∞"
        print(f"  {row['symbol']}: PF={pf_display} | {row['trades']}本 | "
              f"平均={row['avg_pnl']:+.2f}tick | 勝率={row['win_rate']*100:.1f}%")
    print()
    
    # 5. 平均PnL分布
    print("【5】平均PnL分布（トレード数5本以上）")
    print("-" * 70)
    
    avg_pnl_negative = valid_symbols[valid_symbols['avg_pnl'] < 0]
    avg_pnl_0_to_2 = valid_symbols[(valid_symbols['avg_pnl'] >= 0) & (valid_symbols['avg_pnl'] < 2)]
    avg_pnl_2_to_5 = valid_symbols[(valid_symbols['avg_pnl'] >= 2) & (valid_symbols['avg_pnl'] < 5)]
    avg_pnl_above_5 = valid_symbols[valid_symbols['avg_pnl'] >= 5]
    
    print(f"  平均PnL < 0     : {len(avg_pnl_negative):2d}銘柄 ({len(avg_pnl_negative)/len(valid_symbols)*100:4.1f}%)")
    print(f"  平均PnL 0-2    : {len(avg_pnl_0_to_2):2d}銘柄 ({len(avg_pnl_0_to_2)/len(valid_symbols)*100:4.1f}%)")
    print(f"  平均PnL 2-5    : {len(avg_pnl_2_to_5):2d}銘柄 ({len(avg_pnl_2_to_5)/len(valid_symbols)*100:4.1f}%)")
    print(f"  平均PnL ≥ 5    : {len(avg_pnl_above_5):2d}銘柄 ({len(avg_pnl_above_5)/len(valid_symbols)*100:4.1f}%)")
    print()
    
    # 6. 総合判定
    print("=" * 70)
    print("【総合判定】")
    print("=" * 70)
    
    checks = []
    
    # Check 1: Top1集中度
    if top1_pct < 15:
        checks.append(("✅", f"Top1銘柄集中度: {top1_pct:.1f}% < 15%"))
    else:
        checks.append(("⚠️", f"Top1銘柄集中度: {top1_pct:.1f}% ≥ 15%（過集中）"))
    
    # Check 2: PF<1の銘柄比率
    if pf_below_1_pct < 50:
        checks.append(("✅", f"PF<1の銘柄: {pf_below_1_pct:.1f}% < 50%"))
    else:
        checks.append(("⚠️", f"PF<1の銘柄: {pf_below_1_pct:.1f}% ≥ 50%（過半数）"))
    
    # Check 3: 平均PnL負の銘柄比率
    avg_pnl_negative_pct = len(avg_pnl_negative) / len(valid_symbols) * 100 if len(valid_symbols) > 0 else 0
    if avg_pnl_negative_pct < 40:
        checks.append(("✅", f"平均PnL負の銘柄: {avg_pnl_negative_pct:.1f}% < 40%"))
    else:
        checks.append(("⚠️", f"平均PnL負の銘柄: {avg_pnl_negative_pct:.1f}% ≥ 40%"))
    
    print()
    for status, msg in checks:
        print(f"{status} {msg}")
    
    print()
    all_pass = all(status == "✅" for status, _ in checks)
    if all_pass:
        print("✅ 合格: 銘柄分布は健全です")
    else:
        print("⚠️ 注意: 一部基準未達の項目があります")
    
    print()
    print("=" * 70)
    
    # 詳細データを返す
    return stats_df

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_symbol_distribution.py <run_dir>")
        sys.exit(1)
    
    run_dir = sys.argv[1]
    analyze_symbol_distribution(run_dir)
