#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""レベル設定確認スクリプト"""
import yaml
from pathlib import Path

config_path = Path(__file__).parent / "config" / "level_config.yaml"
config = yaml.safe_load(open(config_path, 'r', encoding='utf-8'))

print("=== 現在有効なレベルタイプ ===\n")

for level_type, settings in config['level_types'].items():
    status = "✓ 有効" if settings['enable'] else "✗ 無効"
    weight = settings['weight']
    desc = settings['description']
    print(f"{status:8s} {level_type:15s} (重み: {weight}) - {desc}")

print("\n=== レベルフィルター設定 ===\n")
common = config['common']
print(f"銘柄あたりの最大レベル数: {common['max_levels_per_symbol']}")
print(f"最小重み: {common['quality_filter']['min_weight']}")
print(f"レベル有効期限: {common['level_expiry_days']}営業日")
print(f"重み半減期: {common['weight_decay']['half_life_days']}営業日")

print("\n=== 詳細設定 ===\n")
print(f"Pivot S/R 参照期間: {config['pivot_sr']['lookback_days']}営業日")
print(f"Consolidation 参照期間: {config['consolidation']['lookback_days']}営業日")
print(f"データリーク防止: {'有効' if config['data_leak_prevention']['strict_cutoff'] else '無効'}")

