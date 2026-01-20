#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd

df = pd.read_csv('output/ohlc_1min.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print('=' * 60)
print('【現在のデータ期間】')
print('=' * 60)
print(f'開始: {df["timestamp"].min()}')
print(f'終了: {df["timestamp"].max()}')
print(f'日数: {(df["timestamp"].max() - df["timestamp"].min()).days}日')

print('\n銘柄別:')
for sym in sorted(df['symbol'].unique()):
    sym_df = df[df['symbol'] == sym]
    days = (sym_df['timestamp'].max() - sym_df['timestamp'].min()).days
    hours = (sym_df['timestamp'].max() - sym_df['timestamp'].min()).total_seconds() / 3600
    print(f'{sym:10s}: {days}日 ({hours:.1f}時間)')

print('\n' + '=' * 60)
print('【問題点】')
print('=' * 60)
print('- 現在は1日分（約13時間）のデータのみ')
print('- 数日前の価格帯を検出するには複数日のデータが必要')
print('- 日足での出来高分析には日足データが必要')
