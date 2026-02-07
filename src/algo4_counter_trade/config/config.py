#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
バックテスト・戦略用 Config クラス

- デフォルトパラメータを保持
- 必要に応じて属性で上書き可能
"""

from types import SimpleNamespace

class Config:
    def __init__(self):
        # デフォルトパラメータ
        self.k_tick = 5.0
        self.x_tick = 10.0
        self.y_tick = 5.0
        self.max_hold_bars = 60
        self.strength_th = 0.5
        self.roll_n = 20
        self.k_depth = 5
        # strategy属性はSimpleNamespaceで柔軟に拡張
        self.strategy = SimpleNamespace()
        self.strategy.stop_pct = 0.005
        self.strategy.risk_rr = 1.5
        # 必要に応じて他のパラメータも追加
