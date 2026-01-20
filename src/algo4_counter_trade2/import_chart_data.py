#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
get_rss_chart_dataから取得した日足・分足データをalgo4_counter_trade2にコピー
"""
import os
import shutil
import glob

SOURCE_DIR = os.path.join(os.path.dirname(__file__), '..', 'get_rss_chart_data', 'output')
TARGET_DIR = os.path.join(os.path.dirname(__file__), 'input', 'chart_data')

os.makedirs(TARGET_DIR, exist_ok=True)

def main():
    print("=== チャートデータインポート ===\n")
    
    # 日足データをコピー
    day_source = os.path.join(SOURCE_DIR, 'D_3000_20260119')
    if os.path.exists(day_source):
        print("【日足データ】")
        for csv_file in glob.glob(os.path.join(day_source, '*.csv')):
            filename = os.path.basename(csv_file)
            target_path = os.path.join(TARGET_DIR, filename)
            shutil.copy2(csv_file, target_path)
            print(f"  Copied: {filename}")
    else:
        print(f"WARNING: {day_source} not found")
    
    print()
    
    # 3分足データをコピー
    min3_source = os.path.join(SOURCE_DIR, '3M_3000_20260119')
    if os.path.exists(min3_source):
        print("【3分足データ】")
        for csv_file in glob.glob(os.path.join(min3_source, '*.csv')):
            filename = os.path.basename(csv_file)
            target_path = os.path.join(TARGET_DIR, filename)
            shutil.copy2(csv_file, target_path)
            print(f"  Copied: {filename}")
    else:
        print(f"WARNING: {min3_source} not found")
    
    print()
    print(f"=== 完了 ===")
    print(f"コピー先: {TARGET_DIR}")

if __name__ == "__main__":
    main()
