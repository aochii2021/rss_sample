"""
日次ドローダウン分析（最重要・ロット設計用）
- 最大日次ドローダウン
- 日次PnL分布
- 連続マイナス日数
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path

def analyze_daily_drawdown(run_dir: str):
    """日次ドローダウンを分析"""
    trades_path = Path(run_dir) / 'output' / 'trades.csv'
    
    if not trades_path.exists():
        print(f"❌ {trades_path} が見つかりません")
        return
    
    df = pd.read_csv(trades_path)
    
    # entry_tsから日付を抽出
    df['entry_date'] = pd.to_datetime(df['entry_ts']).dt.date
    
    # 日次PnL集計
    daily_pnl = df.groupby('entry_date')['pnl_tick'].agg([
        ('total_pnl', 'sum'),
        ('trades', 'count'),
        ('avg_pnl', 'mean')
    ]).reset_index()
    
    daily_pnl = daily_pnl.sort_values('entry_date')
    daily_pnl['cumsum'] = daily_pnl['total_pnl'].cumsum()
    
    # 日次ドローダウン計算
    daily_pnl['peak'] = daily_pnl['cumsum'].cummax()
    daily_pnl['drawdown'] = daily_pnl['cumsum'] - daily_pnl['peak']
    
    print("=" * 70)
    print("📉 日次ドローダウン分析（v1.0 ロット設計用）")
    print("=" * 70)
    print()
    
    # 1. 日次PnL基本統計
    print("【1】日次PnL基本統計")
    print("-" * 70)
    print(f"総営業日数: {len(daily_pnl)}日")
    print(f"総PnL: {daily_pnl['total_pnl'].sum():.1f} tick")
    print(f"総トレード数: {daily_pnl['trades'].sum()}本")
    print()
    
    print(f"📊 日次PnL統計:")
    print(f"  平均: {daily_pnl['total_pnl'].mean():+.1f} tick/日")
    print(f"  中央値: {daily_pnl['total_pnl'].median():+.1f} tick/日")
    print(f"  標準偏差: {daily_pnl['total_pnl'].std():.1f} tick")
    print(f"  最大: {daily_pnl['total_pnl'].max():+.1f} tick")
    print(f"  最小: {daily_pnl['total_pnl'].min():+.1f} tick")
    print()
    
    # 2. プラス/マイナス日数
    plus_days = daily_pnl[daily_pnl['total_pnl'] > 0]
    minus_days = daily_pnl[daily_pnl['total_pnl'] < 0]
    zero_days = daily_pnl[daily_pnl['total_pnl'] == 0]
    
    print("【2】日次勝敗分布")
    print("-" * 70)
    print(f"プラス日数: {len(plus_days)}日 ({len(plus_days)/len(daily_pnl)*100:.1f}%)")
    print(f"マイナス日数: {len(minus_days)}日 ({len(minus_days)/len(daily_pnl)*100:.1f}%)")
    print(f"ゼロ日数: {len(zero_days)}日 ({len(zero_days)/len(daily_pnl)*100:.1f}%)")
    print()
    
    if len(plus_days) > 0:
        print(f"📈 プラス日平均: {plus_days['total_pnl'].mean():+.1f} tick")
    if len(minus_days) > 0:
        print(f"📉 マイナス日平均: {minus_days['total_pnl'].mean():+.1f} tick")
    print()
    
    # 3. 連続マイナス日数（最重要）
    print("【3】連続マイナス日数（最重要）")
    print("-" * 70)
    
    # 連続マイナスを検出
    daily_pnl['is_minus'] = daily_pnl['total_pnl'] < 0
    daily_pnl['streak_group'] = (daily_pnl['is_minus'] != daily_pnl['is_minus'].shift()).cumsum()
    
    minus_streaks = daily_pnl[daily_pnl['is_minus']].groupby('streak_group').size()
    
    if len(minus_streaks) > 0:
        max_consecutive_minus = minus_streaks.max()
        avg_consecutive_minus = minus_streaks.mean()
        
        print(f"最大連続マイナス日数: {max_consecutive_minus}日")
        print(f"平均連続マイナス日数: {avg_consecutive_minus:.1f}日")
        print()
        
        # 連続マイナスの詳細
        if max_consecutive_minus > 0:
            max_streak_group = minus_streaks.idxmax()
            max_streak_data = daily_pnl[daily_pnl['streak_group'] == max_streak_group]
            
            print(f"📉 最大連敗期間の詳細:")
            print(f"  期間: {max_streak_data['entry_date'].min()} 〜 {max_streak_data['entry_date'].max()}")
            print(f"  累積損失: {max_streak_data['total_pnl'].sum():.1f} tick")
            print(f"  期間中トレード数: {max_streak_data['trades'].sum()}本")
    else:
        print("マイナス日なし")
    
    print()
    
    # 4. 日次ドローダウン（最重要）
    print("【4】日次ドローダウン（最重要）")
    print("-" * 70)
    
    max_dd = daily_pnl['drawdown'].min()
    max_dd_date = daily_pnl[daily_pnl['drawdown'] == max_dd]['entry_date'].values[0]
    
    print(f"最大ドローダウン: {max_dd:.1f} tick")
    print(f"発生日: {max_dd_date}")
    print()
    
    avg_daily_profit = daily_pnl['total_pnl'].mean()
    dd_ratio = abs(max_dd) / avg_daily_profit if avg_daily_profit > 0 else float('inf')
    
    print(f"📊 DD評価:")
    print(f"  平均日次利益: {avg_daily_profit:+.1f} tick/日")
    print(f"  Max DD / 平均日次利益: {dd_ratio:.2f}倍")
    print()
    
    if dd_ratio <= 4:
        print(f"✅ 合格: Max DD ≤ 平均日次利益 × 4（{dd_ratio:.2f}倍 ≤ 4.0）")
    else:
        print(f"⚠️ 注意: Max DD > 平均日次利益 × 4（{dd_ratio:.2f}倍 > 4.0）")
    
    print()
    
    # 5. 日次PnL推移表
    print("【5】日次PnL推移（全期間）")
    print("-" * 70)
    print()
    
    for idx, row in daily_pnl.iterrows():
        status = "🟢" if row['total_pnl'] > 0 else "🔴" if row['total_pnl'] < 0 else "⚪"
        dd_display = f"(DD: {row['drawdown']:+.1f})" if row['drawdown'] < 0 else ""
        
        print(f"{status} {row['entry_date']}: {row['total_pnl']:+6.1f} tick "
              f"({row['trades']:2d}本, 平均{row['avg_pnl']:+.2f}) "
              f"累積{row['cumsum']:+6.1f} {dd_display}")
    
    print()
    
    # 6. 総合判定
    print("=" * 70)
    print("【総合判定】")
    print("=" * 70)
    print()
    
    checks = []
    
    # Check 1: Max DD比率
    if dd_ratio <= 4:
        checks.append(("✅", f"Max DD比率: {dd_ratio:.2f}倍 ≤ 4.0"))
    else:
        checks.append(("⚠️", f"Max DD比率: {dd_ratio:.2f}倍 > 4.0"))
    
    # Check 2: 連続マイナス日数
    if len(minus_streaks) > 0:
        if max_consecutive_minus <= 5:
            checks.append(("✅", f"最大連敗日数: {max_consecutive_minus}日 ≤ 5日"))
        else:
            checks.append(("⚠️", f"最大連敗日数: {max_consecutive_minus}日 > 5日"))
    else:
        checks.append(("✅", "最大連敗日数: 0日（マイナス日なし）"))
    
    # Check 3: プラス日比率
    plus_ratio = len(plus_days) / len(daily_pnl) * 100
    if plus_ratio >= 60:
        checks.append(("✅", f"プラス日比率: {plus_ratio:.1f}% ≥ 60%"))
    else:
        checks.append(("⚠️", f"プラス日比率: {plus_ratio:.1f}% < 60%"))
    
    for status, msg in checks:
        print(f"{status} {msg}")
    
    print()
    
    all_pass = all(status == "✅" for status, _ in checks)
    if all_pass:
        print("✅ 合格: 日次リスクは許容範囲内です")
        print()
        print("📋 ロット設計への示唆:")
        print(f"  - 想定最大DD: {abs(max_dd):.1f} tick")
        print(f"  - 想定連敗期間: {max_consecutive_minus if len(minus_streaks) > 0 else 0}日")
        print(f"  - 1日あたり期待利益: {avg_daily_profit:+.1f} tick")
    else:
        print("⚠️ 注意: 一部基準未達の項目があります")
    
    print()
    print("=" * 70)
    
    return daily_pnl

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_daily_drawdown.py <run_dir>")
        sys.exit(1)
    
    run_dir = sys.argv[1]
    analyze_daily_drawdown(run_dir)
