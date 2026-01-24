#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分足データ診断"""
import pandas as pd
import glob
import os

print("=== 分足データ診断 ===\n")

files = sorted(glob.glob('input/chart_data/stock_chart_3M_*.csv'))
print(f"分足ファイル数: {len(files)}\n")

for f in files:
    df = pd.read_csv(f, encoding='utf-8-sig')
    symbol = os.path.basename(f).split('_')[3]
    
    if '日付' in df.columns:
        df['日付'] = pd.to_datetime(df['日付'])
        num_days = df['日付'].dt.date.nunique()
        min_date = df['日付'].min()
        max_date = df['日付'].max()
    else:
        num_days = 0
        min_date = "N/A"
        max_date = "N/A"
    
    print(f"■ {symbol}")
    print(f"  行数: {len(df)}行")
    print(f"  期間: {min_date} ～ {max_date}")
    print(f"  日数: {num_days}日")
    
    if '高値' in df.columns and '安値' in df.columns:
        print(f"  価格帯: {df['安値'].min():.0f}～{df['高値'].max():.0f}円")
    
    if '出来高' in df.columns:
        total_vol = df['出来高'].sum()
        print(f"  総出来高: {total_vol:,.0f}")
    
    print()
