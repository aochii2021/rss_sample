import pandas as pd

df = pd.read_csv('input/chart_data/stock_chart_3M_215A_20251208_20260119.csv', encoding='utf-8-sig')
print(f'総行数: {len(df)}')
print(f'出来高>0の行数: {(df["出来高"] > 0).sum()}')
print(f'終値がNaNでない行数: {df["終値"].notna().sum()}')
print(f'\n出来高統計:')
print(df["出来高"].describe())
print(f'\n終値がある行の例:')
print(df[df["終値"].notna()].head(10))
