"""
連敗トレード数分析（ロット設計の最終ピース）
- 最大連敗トレード数
- 平均連敗トレード数
- 連敗時の累積損失
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path

def analyze_losing_streak(run_dir: str):
    """連敗トレード数を分析"""
    trades_path = Path(run_dir) / 'output' / 'trades.csv'
    
    if not trades_path.exists():
        print(f"❌ {trades_path} が見つかりません")
        return
    
    df = pd.read_csv(trades_path)
    df['entry_ts'] = pd.to_datetime(df['entry_ts'])
    df = df.sort_values('entry_ts')
    
    print("=" * 70)
    print("🔴 連敗トレード数分析（v1.0 ロット設計用）")
    print("=" * 70)
    print()
    
    # 1. 基本統計
    print("【1】基本統計")
    print("-" * 70)
    
    total_trades = len(df)
    wins = df[df['pnl_tick'] > 0]
    losses = df[df['pnl_tick'] < 0]
    evens = df[df['pnl_tick'] == 0]
    
    print(f"総トレード数: {total_trades}本")
    print(f"勝ち: {len(wins)}本 ({len(wins)/total_trades*100:.1f}%)")
    print(f"負け: {len(losses)}本 ({len(losses)/total_trades*100:.1f}%)")
    print(f"引分: {len(evens)}本 ({len(evens)/total_trades*100:.1f}%)")
    print()
    
    print(f"平均PnL: {df['pnl_tick'].mean():+.2f} tick")
    print(f"平均勝ち: {wins['pnl_tick'].mean():+.2f} tick")
    print(f"平均負け: {losses['pnl_tick'].mean():+.2f} tick")
    print()
    
    # 2. 連敗検出
    print("【2】連敗検出（最重要）")
    print("-" * 70)
    
    # 負けフラグ
    df['is_loss'] = df['pnl_tick'] < 0
    df['streak_group'] = (df['is_loss'] != df['is_loss'].shift()).cumsum()
    
    # 連敗グループのみ抽出
    losing_streaks = df[df['is_loss']].groupby('streak_group').agg({
        'pnl_tick': ['count', 'sum'],
        'entry_ts': ['min', 'max']
    })
    
    if len(losing_streaks) > 0:
        losing_streaks.columns = ['streak_length', 'cumulative_loss', 'start_time', 'end_time']
        losing_streaks = losing_streaks.sort_values('streak_length', ascending=False)
        
        max_streak = losing_streaks['streak_length'].max()
        avg_streak = losing_streaks['streak_length'].mean()
        median_streak = losing_streaks['streak_length'].median()
        
        print(f"連敗グループ数: {len(losing_streaks)}回")
        print()
        print(f"📊 連敗統計:")
        print(f"  最大連敗: {max_streak:.0f}本")
        print(f"  平均連敗: {avg_streak:.1f}本")
        print(f"  中央値連敗: {median_streak:.0f}本")
        print()
        
        # 連敗分布
        print(f"📈 連敗長さ分布:")
        streak_dist = losing_streaks['streak_length'].value_counts().sort_index()
        for length, count in streak_dist.items():
            pct = count / len(losing_streaks) * 100
            bar = "█" * int(pct / 5)
            print(f"  {length:2.0f}本: {count:3d}回 ({pct:5.1f}%) {bar}")
        
        print()
        
        # 3. 最大連敗期間の詳細
        print("【3】最大連敗期間の詳細")
        print("-" * 70)
        
        max_streak_row = losing_streaks.iloc[0]
        max_streak_group = losing_streaks.index[0]
        max_streak_trades = df[df['streak_group'] == max_streak_group]
        
        print(f"最大連敗: {max_streak_row['streak_length']:.0f}本")
        print(f"期間: {max_streak_row['start_time'].strftime('%Y-%m-%d %H:%M')} 〜 {max_streak_row['end_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"累積損失: {max_streak_row['cumulative_loss']:.1f} tick")
        print(f"平均損失: {max_streak_row['cumulative_loss'] / max_streak_row['streak_length']:.2f} tick/本")
        print()
        
        print(f"📉 連敗期間トレード詳細:")
        for idx, trade in max_streak_trades.iterrows():
            print(f"  {trade['entry_ts'].strftime('%Y-%m-%d %H:%M')} {trade['symbol']:5s} "
                  f"{trade['pnl_tick']:+6.1f}tick ({trade['exit_reason']:10s})")
        
        print()
        
        # 4. 連敗Top5
        print("【4】連敗Top5（長さ順）")
        print("-" * 70)
        
        top5_streaks = losing_streaks.head(5)
        for idx, (group_id, row) in enumerate(top5_streaks.iterrows(), 1):
            print(f"{idx}. {row['streak_length']:.0f}本連敗: "
                  f"{row['start_time'].strftime('%Y-%m-%d')} 〜 {row['end_time'].strftime('%Y-%m-%d')} "
                  f"| 累積損失: {row['cumulative_loss']:.1f}tick")
        
        print()
        
        # 5. 日次利益との比較（重要）
        print("【5】連敗損失 vs 日次利益（ロット計算用）")
        print("-" * 70)
        
        # 日次PnL計算
        df['entry_date'] = df['entry_ts'].dt.date
        daily_pnl = df.groupby('entry_date')['pnl_tick'].sum()
        avg_daily_profit = daily_pnl.mean()
        
        max_streak_loss = abs(max_streak_row['cumulative_loss'])
        loss_vs_daily = max_streak_loss / avg_daily_profit if avg_daily_profit > 0 else float('inf')
        
        print(f"平均日次利益: {avg_daily_profit:+.1f} tick/日")
        print(f"最大連敗時損失: {max_streak_loss:.1f} tick")
        print(f"損失 / 日次利益: {loss_vs_daily:.2f}倍")
        print()
        
        if loss_vs_daily <= 1.0:
            print(f"✅ 優秀: 最大連敗損失 ≤ 1日分利益（{loss_vs_daily:.2f}倍 ≤ 1.0）")
        elif loss_vs_daily <= 1.5:
            print(f"✅ 合格: 最大連敗損失 ≤ 1.5日分利益（{loss_vs_daily:.2f}倍 ≤ 1.5）")
        else:
            print(f"⚠️ 注意: 最大連敗損失 > 1.5日分利益（{loss_vs_daily:.2f}倍 > 1.5）")
        
        print()
        
        # 6. 総合判定
        print("=" * 70)
        print("【総合判定】")
        print("=" * 70)
        print()
        
        checks = []
        
        # Check 1: 最大連敗数
        if max_streak <= 10:
            checks.append(("✅", f"最大連敗: {max_streak:.0f}本 ≤ 10本"))
        else:
            checks.append(("⚠️", f"最大連敗: {max_streak:.0f}本 > 10本"))
        
        # Check 2: 連敗損失比率
        if loss_vs_daily <= 1.5:
            checks.append(("✅", f"連敗損失比率: {loss_vs_daily:.2f}倍 ≤ 1.5"))
        else:
            checks.append(("⚠️", f"連敗損失比率: {loss_vs_daily:.2f}倍 > 1.5"))
        
        # Check 3: 平均連敗
        if avg_streak <= 3:
            checks.append(("✅", f"平均連敗: {avg_streak:.1f}本 ≤ 3本"))
        else:
            checks.append(("⚠️", f"平均連敗: {avg_streak:.1f}本 > 3本"))
        
        for status, msg in checks:
            print(f"{status} {msg}")
        
        print()
        
        all_pass = all(status == "✅" for status, _ in checks)
        if all_pass:
            print("✅ 合格: 連敗リスクは許容範囲内です")
            print()
            print("📋 ロット設計への示唆:")
            print(f"  - 想定最大連敗: {max_streak:.0f}本")
            print(f"  - 想定最大連敗時損失: {max_streak_loss:.1f} tick")
            print(f"  - 平均日次利益: {avg_daily_profit:+.1f} tick/日")
            print(f"  - 損失回復日数: {loss_vs_daily:.2f}日分")
            print()
            print("💡 推奨ロット設計:")
            print(f"  - 安全係数: 最大連敗×2 = {max_streak*2:.0f}本分の損失に耐える資金")
            print(f"  - 1本あたり想定損失: {abs(losses['pnl_tick'].mean()):.1f} tick")
            print(f"  - 必要バッファ: {max_streak*2 * abs(losses['pnl_tick'].mean()):.0f} tick相当")
        else:
            print("⚠️ 注意: 一部基準未達の項目があります")
        
        print()
        print("=" * 70)
        
        return {
            'max_streak': max_streak,
            'avg_streak': avg_streak,
            'max_streak_loss': max_streak_loss,
            'avg_daily_profit': avg_daily_profit,
            'loss_vs_daily': loss_vs_daily
        }
    
    else:
        print("🎉 連敗なし（全勝または引分のみ）")
        print()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_losing_streak.py <run_dir>")
        sys.exit(1)
    
    run_dir = sys.argv[1]
    analyze_losing_streak(run_dir)
