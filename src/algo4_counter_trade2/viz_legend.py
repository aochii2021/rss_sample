#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
可視化の凡例説明
"""

print("=" * 70)
print("【チャート可視化の凡例】")
print("=" * 70)
print()
print("■ エントリーポイント")
print("  ▲ 緑の上向き三角  → 買いエントリー")
print("  ▼ 赤の下向き三角  → 売りエントリー")
print()
print("■ エグジットポイント")
print("  ● 金色の円        → 利確（プラスで決済）")
print("  ● グレーの円      → 損切またはタイムアウト（マイナスで決済）")
print()
print("■ エントリー→エグジットの線")
print("  ━━ 緑の線        → 買いトレード")
print("     実線: 利確 / 破線: 損切")
print("  ━━ 赤の線        → 売りトレード")
print("     実線: 利確 / 破線: 損切")
print("  ※ 線でエントリーとエグジットの対応関係を明示")
print()
print("■ サポート/レジスタンスレベル")
print("  --- 水平線        → S/Rレベル（色と太さは強度による）")
print()
print("=" * 70)
print("【出力ファイル】")
print("  output/figs/ohlc_levels_*.png")
print("=" * 70)
