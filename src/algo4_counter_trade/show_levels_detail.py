#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""レベル詳細表示"""
import json

print("=== 揉み合いゾーン詳細 ===\n")

dates = ['20260119', '20260120']

for date in dates:
    date_str = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    print(f"■ {date_str}")
    
    levels_path = f"output/levels_intraday3d_{date}.jsonl"
    levels = [json.loads(line) for line in open(levels_path, 'r', encoding='utf-8')]
    
    intraday = [lv for lv in levels if lv.get('type', '').startswith('intraday')]
    daily = [lv for lv in levels if lv.get('metadata', {}).get('source') == 'daily_fallback']
    
    print(f"  分足揉み合いゾーン: {len(intraday)}件")
    for lv in intraday:
        meta = lv['metadata']
        print(f"    {meta['date']}: {meta['zone_start']:.1f}～{meta['zone_end']:.1f}円 "
              f"(中心{lv['level_now']:.1f}, 強度{lv['strength']:.2f}, 幅{meta['zone_width']:.1f})")
    
    print(f"  日足補完: {len(daily)}件")
    for lv in daily:
        meta = lv.get('metadata', {})
        if meta:
            print(f"    {meta.get('zone_start', 0):.1f}～{meta.get('zone_end', 0):.1f}円 "
                  f"(中心{lv['level_now']:.1f}, 幅{meta.get('zone_width', 0):.1f})")
    print()
