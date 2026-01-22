import pandas as pd

# stock_code_master.csvから内国株式の全銘柄を抽出
df = pd.read_csv('data/stock_code_master.csv', encoding='utf-8-sig')

# 内国株式のみフィルタ
df_stock = df[df['市場・商品区分'].str.contains('内国株式', na=False)]

print(f'全銘柄数: {len(df_stock)}')
print(f'先頭5件:')
print(df_stock.head())

# watchlist.csvに保存
df_stock.to_csv('src/get_rss_market_order_book/input/watchlist.csv', index=False, encoding='utf-8-sig')
print('\nwatchlist.csv更新完了')
