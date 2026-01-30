# -*- coding: utf-8 -*-
"""
market_order_bookディレクトリ配下のrss_market_data.csvを統合し、重複を除去して保存するスクリプト
"""
import os
import glob
import pandas as pd
from tqdm import tqdm

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/00_raw/market_order_book'))
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/01_processed/market_order_book'))
os.makedirs(PROCESSED_DIR, exist_ok=True)
OUTPUT_PATH = os.path.join(PROCESSED_DIR, 'all_market_order_book.csv')


def collect_and_concat_market_order_book():
    # 各サブディレクトリのrss_market_data.csvを集約
    dirs = glob.glob(os.path.join(RAW_DIR, '*'))
    all_dfs = []
    for d in tqdm(dirs, desc='market_order_book dirs'):
        csv_path = os.path.join(d, 'rss_market_data.csv')
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path, dtype=str)
                all_dfs.append(df)
            except Exception as e:
                print(f"[ERROR] {csv_path}: {e}")
    if not all_dfs:
        print("No data found for market_order_book")
        return
    df_all = pd.concat(all_dfs, ignore_index=True)
    # 記録日時・銘柄コードでユニーク化
    df_all = df_all.drop_duplicates(subset=['記録日時', '銘柄コード'])
    df_all.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
    print(f"Saved: {OUTPUT_PATH} ({len(df_all)} rows)")


def main():
    collect_and_concat_market_order_book()

if __name__ == '__main__':
    main()
