"""見つからなかった銘柄を特定"""
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

# stock_code_master.csvを読み込み
master_df = pd.read_csv('data/stock_code_master.csv', dtype=str)

# マスターデータの日付を確認
print(f"マスターデータの日付: {master_df['日付'].iloc[0]}")
print(f"マスターデータ件数: {len(master_df)}")
print()

# マスターデータに存在する銘柄コードのセット
master_codes = set(master_df['コード'].values)

# 見つからなかった銘柄を特定
missing_codes = [code for code in daytrade_codes if code not in master_codes]

print(f"デイトレ銘柄数: {len(daytrade_codes)}")
print(f"見つかった銘柄数: {len(daytrade_codes) - len(missing_codes)}")
print(f"見つからなかった銘柄数: {len(missing_codes)}")

if missing_codes:
    print(f"\n見つからなかった銘柄コード:")
    for code in missing_codes:
        print(f"  {code}")
    
    # 部分一致で探してみる
    print(f"\n参考：部分一致する銘柄:")
    for code in missing_codes:
        base_code = code.rstrip('A')  # 末尾のAを除去
        partial_matches = master_df[master_df['コード'].str.contains(base_code, na=False)]
        if len(partial_matches) > 0:
            print(f"  {code} に似た銘柄:")
            for _, row in partial_matches.head(5).iterrows():
                print(f"    {row['コード']} - {row['銘柄名']}")
