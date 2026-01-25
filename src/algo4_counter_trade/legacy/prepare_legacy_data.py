#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Legacy版バックテスト用のデータ準備スクリプト
新版のデータ構造からlegacy版に必要なフォーマットでデータを抽出
"""
import sys
import os
import pandas as pd

# 親ディレクトリをパスに追加
algo4_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, algo4_dir)
os.chdir(algo4_dir)

from data_processing.data_loader import DataLoader
from core.level_generator import LevelGenerator
from config.level_config import LevelConfig
import json

def main():
    print("=== Legacy版データ準備 ===\n")
    
    # 出力先
    output_dir = "runs/legacy_reproduce_20260124_201510/output"
    os.makedirs(output_dir, exist_ok=True)
    
    # DataLoader初期化
    loader = DataLoader('market_data/chart_data', 'market_data/market_order_book')
    
    # チャートデータ読み込み（3分足、全銘柄、直近日付）
    print("チャートデータ読み込み中...")
    chart_df = loader.load_chart_data('3M', '3000', ['20260123'])
    print(f"  - {len(chart_df)} rows, {len(chart_df['symbol'].unique())} symbols")
    
    # OHLC保存
    ohlc_path = os.path.join(output_dir, "ohlc_combined.csv")
    chart_df.to_csv(ohlc_path, index=False)
    print(f"✓ Saved: {ohlc_path}")
    
    # レベル生成（全レベルタイプ有効）
    print("\nS/Rレベル生成中...")
    level_config = LevelConfig()
    # 全レベルタイプを有効化
    for level_type in level_config.level_types.keys():
        if level_type != 'vpoc':  # vpocは未実装
            level_config.level_types[level_type]['enable'] = True
    
    level_gen = LevelGenerator(level_config)
    
    # 銘柄ごとにレベル生成
    all_levels = []
    symbols = chart_df['symbol'].unique()
    for symbol in symbols:
        symbol_chart = chart_df[chart_df['symbol'] == symbol].copy()
        # 日付ごとに生成（データリーク防止）
        dates = symbol_chart['datetime'].dt.date.unique()
        for date in dates:
            cutoff = pd.Timestamp(date)
            historical = symbol_chart[symbol_chart['datetime'] < cutoff]
            if len(historical) < 10:  # 最低限のデータ必要
                continue
            levels = level_gen.generate_levels(historical, symbol, str(date))
            all_levels.extend(levels)
    
    print(f"  - {len(all_levels)} levels generated for {len(symbols)} symbols")
    
    # JSONL形式で保存
    levels_path = os.path.join(output_dir, "levels.jsonl")
    with open(levels_path, 'w', encoding='utf-8') as f:
        for level in all_levels:
            f.write(json.dumps(level, ensure_ascii=False) + '\n')
    print(f"✓ Saved: {levels_path}")
    
    # LOB features はすでに生成済み
    lob_path = os.path.join(output_dir, "lob_features.csv")
    if os.path.exists(lob_path):
        lob_df = pd.read_csv(lob_path)
        print(f"\n✓ LOB features already exists: {len(lob_df)} rows")
    else:
        print(f"\n⚠ LOB features not found: {lob_path}")
    
    print("\n=== データ準備完了 ===")
    print(f"Output directory: {output_dir}")
    print(f"  - lob_features.csv: 70168 rows")
    print(f"  - ohlc_combined.csv: {len(chart_df)} rows")
    print(f"  - levels.jsonl: {len(all_levels)} levels")

if __name__ == "__main__":
    main()
