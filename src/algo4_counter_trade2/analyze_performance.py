import pandas as pd

df = pd.read_csv('output/trades_5d_combined.csv')
df['date'] = pd.to_datetime(df['entry_ts']).dt.date

# 日別銘柄別
summary = df.groupby(['date', 'symbol']).agg({
    'pnl_tick': ['count', 'sum', 'mean'],
    'exit_reason': lambda x: (x.str.contains('TP', na=False)).sum()
}).round(2)
summary.columns = ['トレード数', '総損益(tick)', '平均(tick)', 'TP回数']
summary['勝率(%)'] = (df.groupby(['date', 'symbol'])['pnl_tick']
                      .apply(lambda x: (x > 0).sum() / len(x) * 100)).round(1)

print("=== 日別・銘柄別パフォーマンス ===")
print(summary.to_string())

# 銘柄別合計
print('\n=== 銘柄別合計 ===')
summary2 = df.groupby('symbol').agg({
    'pnl_tick': ['count', 'sum', 'mean'],
    'exit_reason': lambda x: (x.str.contains('TP', na=False)).sum()
}).round(2)
summary2.columns = ['トレード数', '総損益(tick)', '平均(tick)', 'TP回数']
summary2['勝率(%)'] = (df.groupby('symbol')['pnl_tick']
                       .apply(lambda x: (x > 0).sum() / len(x) * 100)).round(1)
print(summary2.to_string())

# 全体サマリー
print('\n=== 全体サマリー ===')
print(f'総トレード数: {len(df)}')
print(f'勝率: {(df["pnl_tick"] > 0).sum() / len(df) * 100:.1f}%')
print(f'総損益: {df["pnl_tick"].sum():.2f} tick')
print(f'平均損益: {df["pnl_tick"].mean():.2f} tick')

# レベルタイプ別の統計（level_countがある場合）
if 'level_count' in df.columns:
    print('\n=== レベル重複数別 ===')
    level_stats = df.groupby('level_count').agg({
        'pnl_tick': ['count', 'mean', 'sum']
    }).round(2)
    level_stats.columns = ['トレード数', '平均損益', '総損益']
    level_stats['勝率(%)'] = (df.groupby('level_count')['pnl_tick']
                              .apply(lambda x: (x > 0).sum() / len(x) * 100)).round(1)
    print(level_stats.to_string())
