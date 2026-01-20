#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
複数日のマーケットデータを結合して重複を削除
input/market_order_book/YYYYMMDD/rss_market_data.csv を結合
"""
import argparse
import os
import pandas as pd
from pathlib import Path

def merge_market_data(input_dir: str, output_path: str):
    """複数日のマーケットデータを結合"""
    input_path = Path(input_dir)
    
    # 日付ディレクトリをスキャン
    date_dirs = sorted([d for d in input_path.iterdir() if d.is_dir() and d.name.isdigit()])
    
    if not date_dirs:
        raise ValueError(f"日付ディレクトリが見つかりません: {input_dir}")
    
    print(f"検出された日付ディレクトリ: {[d.name for d in date_dirs]}")
    
    dfs = []
    for date_dir in date_dirs:
        csv_path = date_dir / "rss_market_data.csv"
        if csv_path.exists():
            print(f"読み込み中: {csv_path}")
            df = pd.read_csv(csv_path)
            dfs.append(df)
        else:
            print(f"WARNING: ファイルが見つかりません: {csv_path}")
    
    if not dfs:
        raise ValueError("読み込めるCSVファイルがありません")
    
    # 結合
    print(f"\n結合中: {len(dfs)}ファイル")
    merged = pd.concat(dfs, ignore_index=True)
    print(f"結合後の行数: {len(merged)}")
    
    # 重複削除（記録日時 + 銘柄コードで判定）
    if '記録日時' in merged.columns and '銘柄コード' in merged.columns:
        before = len(merged)
        merged = merged.drop_duplicates(subset=['記録日時', '銘柄コード'], keep='first')
        removed = before - len(merged)
        print(f"重複削除: {removed}行削除")
        print(f"最終行数: {len(merged)}")
    else:
        print("WARNING: 重複削除できません（記録日時または銘柄コードがありません）")
    
    # タイムスタンプでソート
    if '記録日時' in merged.columns:
        merged['記録日時'] = pd.to_datetime(merged['記録日時'])
        merged = merged.sort_values('記録日時').reset_index(drop=True)
        print(f"期間: {merged['記録日時'].min()} ～ {merged['記録日時'].max()}")
    
    # 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    merged.to_csv(output_path, index=False)
    print(f"\n保存完了: {output_path}")
    
    return merged

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default="input/market_order_book",
                    help="マーケットデータの親ディレクトリ")
    ap.add_argument("--output", default="input/rss_market_data_merged.csv",
                    help="出力CSVパス")
    args = ap.parse_args()
    
    merge_market_data(args.input_dir, args.output)

if __name__ == "__main__":
    main()
