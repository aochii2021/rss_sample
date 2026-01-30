# -*- coding: utf-8 -*-
"""
chart_dataディレクトリ配下の3分足(3M_*)・日足(D_*)データを統合し、重複を除去して保存するスクリプト
"""
import os
import glob
import pandas as pd
from tqdm import tqdm


RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/00_raw/chart_data'))
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/01_processed/chart_data'))
os.makedirs(PROCESSED_DIR, exist_ok=True)
OUTPUT_3M = os.path.join(PROCESSED_DIR, 'all_3M.csv')
OUTPUT_D = os.path.join(PROCESSED_DIR, 'all_D.csv')

def collect_and_concat(pattern, output_path, unique_cols):
	dirs = glob.glob(os.path.join(RAW_DIR, pattern))
	all_dfs = []
	for d in tqdm(dirs, desc=f"{pattern} dirs"):
		csvs = glob.glob(os.path.join(d, '*.csv'))
		for csv in csvs:
			try:
				df = pd.read_csv(csv, dtype=str)
				all_dfs.append(df)
			except Exception as e:
				print(f"[ERROR] {csv}: {e}")
	if not all_dfs:
		print(f"No data found for {pattern}")
		return
	df_all = pd.concat(all_dfs, ignore_index=True)
	# ユニーク化
	df_all = df_all.drop_duplicates(subset=unique_cols)
	df_all.to_csv(output_path, index=False, encoding='utf-8-sig')
	print(f"Saved: {output_path} ({len(df_all)} rows)")

def main():
	# 3分足
	collect_and_concat('3M_*', OUTPUT_3M, unique_cols=['銘柄コード', '日付', '時刻'])
	# 日足
	collect_and_concat('D_*', OUTPUT_D, unique_cols=['銘柄コード', '日付', '時刻'])

if __name__ == '__main__':
	main()
