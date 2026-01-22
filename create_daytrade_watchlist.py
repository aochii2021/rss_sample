"""デイトレ銘柄100銘柄のwatchlistを作成"""
import pandas as pd

# デイトレ銘柄の銘柄コードリスト
daytrade_codes = [
    '285A', '9984', '6146', '6920', '6857', '5016', '8035', '5803', '7280', '7013',
    '7012', '4082', '3110', '7011', '6330', '5706', '9501', '8306', '7974', '7735',
    '6525', '5713', '5801', '4584', '7003', '6993', '6081', '4062', '5802', '6963',
    '8411', '8267', '4098', '7746', '6269', '4004', '5332', '7771', '7203', '8316',
    '6723', '6758', '5707', '6590', '6273', '6506', '5216', '9983', '4506', '6890',
    '6367', '6954', '7729', '6501', '4107', '8136', '6315', '6871', '3436', '6762',
    '6323', '6166', '3692', '6701', '6098', '8303', '2667', '6361', '4063', '202A',
    '4593', '4237', '168A', '6752', '5243', '7182', '3350', '5631', '6702', '8766',
    '1812', '8058', '7014', '6814', '5401', '9250', '485A', '7779', '4507', '6861',
    '7911', '1801', '7731', '157A', '4531', '198A', '3647', '2768', '3697', '7711'
]

# stock_code_master.csvから該当銘柄を抽出
master_df = pd.read_csv('data/stock_code_master.csv', dtype=str)
print(f"マスターデータ件数: {len(master_df)}")

# 銘柄コードでフィルタリング
watchlist_df = master_df[master_df['コード'].isin(daytrade_codes)].copy()

# 元の順序を保持するために、daytrade_codesの順序でソート
watchlist_df['sort_key'] = watchlist_df['コード'].apply(lambda x: daytrade_codes.index(x) if x in daytrade_codes else 999)
watchlist_df = watchlist_df.sort_values('sort_key').drop('sort_key', axis=1)

print(f"抽出された銘柄数: {len(watchlist_df)}")
print(f"\n先頭5件:")
print(watchlist_df.head())

# watchlist.csvに保存
output_path = 'src/get_rss_market_order_book/input/watchlist.csv'
watchlist_df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\n{output_path} に保存しました")
