#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json

with open('output/optimized_params_trading_hours.json') as f:
    params = json.load(f)

print('# 営業時間フィルタ適用後の最適化パラメータ (9:00-15:00)')
print('SYMBOL_PARAMS = {')
for symbol, data in params.items():
    bp = data['best_params']
    print(f'    "{symbol}": {{')
    print(f'        "k_tick": {bp["k_tick"]},')
    print(f'        "x_tick": {bp["x_tick"]},')
    print(f'        "y_tick": {bp["y_tick"]},')
    print(f'        "max_hold_bars": {bp["max_hold_bars"]},')
    print(f'        "roll_n": {bp["roll_n"]},')
    print(f'        "k_depth": {bp["k_depth"]}')
    print(f'    }},')
print('}')
