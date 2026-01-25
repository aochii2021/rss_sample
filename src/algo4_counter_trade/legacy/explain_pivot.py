#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ピボット高値・安値の説明と視覚化スクリプト
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from pathlib import Path

# 日本語フォント設定
plt.rcParams["font.sans-serif"] = ["Yu Gothic", "MS Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

print("=" * 60)
print("ピボット高値・安値とは")
print("=" * 60)
print("""
【定義】
ピボット高値・安値は、価格チャート上で周囲よりも明確に高い（または低い）
価格ポイントのことです。テクニカル分析において、重要なサポート・レジスタンス
レベルとして機能します。

【本システムでの実装】
1. 過去5営業日分のローソク足データを参照
2. scipy.signal.find_peaks()を使用してピーク検出
3. パラメータ:
   - min_distance: 2本（ピーク間の最小距離）
   - prominence: 0.5（ピークの顕著性）

【ピボット高値（Pivot High）】
周囲の高値よりも明確に高い価格ポイント
→ レジスタンス（上値抵抗線）として機能する可能性

【ピボット安値（Pivot Low）】
周囲の安値よりも明確に低い価格ポイント
→ サポート（下値支持線）として機能する可能性

【検出アルゴリズム】
1. 高値のピーク検出: find_peaks(high_prices)
2. 安値のピーク検出: find_peaks(-low_prices)  ← マイナス反転で谷を検出

【使い方】
検出されたピボット高値・安値は、カウンタートレード戦略において
エントリー・エグジットの目標価格として使用されます。
""")

# サンプルデータで視覚化
print("\n簡単な例を図示します...")

# サンプル価格データ
days = 20
np.random.seed(42)
base_price = 1000
price_data = base_price + np.cumsum(np.random.randn(days) * 5)
high_data = price_data + np.random.uniform(2, 8, days)
low_data = price_data - np.random.uniform(2, 8, days)

# ピーク検出
high_peaks, _ = find_peaks(high_data, distance=2, prominence=3)
low_peaks, _ = find_peaks(-low_data, distance=2, prominence=3)

# プロット
fig, ax = plt.subplots(figsize=(14, 8))

# 価格バンド
ax.fill_between(range(days), low_data, high_data, alpha=0.3, color='gray', label='価格範囲')
ax.plot(range(days), price_data, 'k-', linewidth=2, label='終値')

# ピボット高値
for peak in high_peaks:
    ax.plot(peak, high_data[peak], 'rv', markersize=15, label='ピボット高値' if peak == high_peaks[0] else '')
    ax.axhline(high_data[peak], color='red', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(days + 0.5, high_data[peak], f'  R: {high_data[peak]:.1f}', 
            verticalalignment='center', color='red', fontweight='bold')

# ピボット安値
for peak in low_peaks:
    ax.plot(peak, low_data[peak], 'g^', markersize=15, label='ピボット安値' if peak == low_peaks[0] else '')
    ax.axhline(low_data[peak], color='green', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(days + 0.5, low_data[peak], f'  S: {low_data[peak]:.1f}', 
            verticalalignment='center', color='green', fontweight='bold')

ax.set_xlabel('時間（日数）', fontsize=12)
ax.set_ylabel('価格', fontsize=12)
ax.set_title('ピボット高値・安値の例\n（赤▼: レジスタンス候補、緑▲: サポート候補）', 
             fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=10)
ax.grid(alpha=0.3)
ax.set_xlim(-1, days + 4)

plt.tight_layout()

output_path = Path(__file__).parent / "pivot_explanation.png"
plt.savefig(output_path, dpi=150)
print(f"\n✓ 図を保存しました: {output_path}")
print(f"\n検出されたピボット高値: {len(high_peaks)}個")
print(f"検出されたピボット安値: {len(low_peaks)}個")
