import json
from collections import defaultdict
import pandas as pd

# レベルデータを読み込み
with open('output/levels_with_consolidation.jsonl', encoding='utf-8') as f:
    data = [json.loads(line) for line in f]

# 分足揉み合いレベルを抽出
intraday_levels = [d for d in data if d['kind'] == 'intraday_consolidation']

print(f"=== 分足揉み合い価格帯分析 ===\n")
print(f"総数: {len(intraday_levels)}件\n")

# 銘柄別・日別に集計
by_symbol_date = defaultdict(list)
for level in intraday_levels:
    symbol = level['symbol']
    date = level['meta']['date']
    price = level['level_now']
    strength = level['strength']
    zone_width = level['meta']['zone_width']
    
    by_symbol_date[(symbol, date)].append({
        'price': price,
        'strength': strength,
        'width': zone_width
    })

# 銘柄別に表示
symbols = sorted(set(k[0] for k in by_symbol_date.keys()))
for symbol in symbols:
    print(f"【銘柄: {symbol}】")
    dates = sorted([k[1] for k in by_symbol_date.keys() if k[0] == symbol])
    print(f"  検出日数: {len(dates)}日")
    print(f"  期間: {dates[0]} ～ {dates[-1]}")
    print(f"  揉み合い箇所数: {sum(len(by_symbol_date[(symbol, d)]) for d in dates)}")
    print()
    
    # 最初の3日分を詳細表示
    for i, date in enumerate(dates[:3]):
        levels = by_symbol_date[(symbol, date)]
        print(f"  {date}: {len(levels)}箇所")
        for level in sorted(levels, key=lambda x: -x['strength'])[:3]:
            print(f"    - {level['price']:.1f}円 (強度: {level['strength']:.2f}, 幅: {level['width']:.1f}円)")
    
    if len(dates) > 3:
        print(f"  ... 他 {len(dates)-3}日分")
    print()

# 3分足データの実際の期間を確認
print("\n=== 3分足データ期間確認 ===")
for symbol in symbols[:2]:  # 最初の2銘柄だけチェック
    import glob
    files = glob.glob(f'input/chart_data/stock_chart_3M_{symbol}_*.csv')
    if files:
        df = pd.read_csv(files[0], encoding='utf-8-sig')
        if '日付' in df.columns:
            df['datetime'] = pd.to_datetime(df['日付'] + ' ' + df['時刻'], format='%Y/%m/%d %H:%M', errors='coerce')
            df = df.dropna(subset=['datetime'])
            print(f"{symbol}: {df['datetime'].min()} ～ {df['datetime'].max()}")
            print(f"  総データ数: {len(df)}件")
            unique_dates = df['datetime'].dt.date.nunique()
            print(f"  日数: {unique_dates}日")
