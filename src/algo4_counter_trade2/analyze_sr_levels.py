#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
サポート/レジスタンスレベルの根拠分析
"""
import json
import pandas as pd
from collections import Counter

# レベルデータの読み込み
levels = []
with open('output/levels_by_symbol.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        levels.append(json.loads(line))

df_levels = pd.DataFrame(levels)

print("=" * 70)
print("【サポート/レジスタンスレベルの根拠】")
print("=" * 70)
print()
print("■ 検出手法の種類")
print()

kind_counts = df_levels['kind'].value_counts()
for kind, count in kind_counts.items():
    print(f"  {kind:20s}: {count:3d}個")

print()
print("■ 各手法の説明")
print()
print("1. recent_high / recent_low")
print("   - 直近N本（デフォルト180本=3時間）の高値・安値")
print("   - タッチ回数が多いほど強度が高い")
print()
print("2. vpoc / hvn")
print("   - Volume Profile（価格帯別出来高）のピーク")
print("   - vpoc: 最も出来高が多い価格帯")
print("   - hvn: 出来高が多い価格帯（High Volume Node）")
print()
print("3. swing_resistance / swing_support")
print("   - スイング高値・安値（フラクタル検出）")
print("   - 前後N本より高い（低い）価格帯")
print("   - デフォルト: pivot_left=3, pivot_right=3")
print()
print("4. prev_high / prev_low / prev_close")
print("   - 前日の高値・安値・終値")
print("   - デイトレードでよく意識される水準")
print()
print("=" * 70)
print("【銘柄別のレベル数】")
print("=" * 70)
print()

symbol_counts = df_levels['symbol'].value_counts()
for symbol, count in symbol_counts.items():
    print(f"{symbol:10s}: {count:3d}個")

print()
print("=" * 70)
print("【強度（strength）の分布】")
print("=" * 70)
print()
print(f"平均強度: {df_levels['strength'].mean():.2f}")
print(f"最小強度: {df_levels['strength'].min():.2f}")
print(f"最大強度: {df_levels['strength'].max():.2f}")
print()
print("強度別:")
bins = [0, 0.3, 0.5, 0.7, 0.9, 1.0]
labels = ['0.0-0.3', '0.3-0.5', '0.5-0.7', '0.7-0.9', '0.9-1.0']
df_levels['strength_bin'] = pd.cut(df_levels['strength'], bins=bins, labels=labels)
print(df_levels['strength_bin'].value_counts().sort_index())

print()
print("=" * 70)
