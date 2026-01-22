import json
from collections import Counter

with open('output/levels_with_consolidation.jsonl', encoding='utf-8') as f:
    data = [json.loads(line) for line in f]

kinds = [d['kind'] for d in data]
kind_counts = Counter(kinds)

print(f'総レベル数: {len(data)}')
print()
print('種類別:')
for kind, count in sorted(kind_counts.items(), key=lambda x: -x[1]):
    print(f'  {kind}: {count}')

# 揉み合い系のレベルを詳細表示
print()
print('揉み合い系レベル詳細:')
consolidation_levels = [d for d in data if 'consolidation' in d['kind']]
for level in consolidation_levels[:5]:  # 最初の5件
    print(f"  {level['kind']} - {level['symbol']}: {level['level_now']:.1f}円 (strength: {level['strength']:.2f})")
    if 'meta' in level and 'date' in level['meta']:
        print(f"    日付: {level['meta']['date']}, 幅: {level['meta']['zone_width']:.1f}円")
