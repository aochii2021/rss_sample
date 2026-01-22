#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
シグナル生成
algo4_counter_tradeの戦略ロジックを実トレードに適用
"""
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

# algo4_counter_tradeのモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent / "algo4_counter_trade"))
from sr_levels import extract_levels

import config

logger = logging.getLogger(__name__)


class SignalGenerator:
    """シグナル生成クラス"""
    
    def __init__(self):
        self.k_tick = config.STRATEGY_PARAMS["k_tick"]
        self.strength_threshold = config.STRATEGY_PARAMS["strength_threshold"]
        
        # 銘柄ごとのサポート/レジスタンスレベル
        self.levels_cache = {}
        
        logger.info("SignalGenerator initialized")
    
    def update_levels(self, symbol: str, ohlc_df: pd.DataFrame):
        """
        サポート/レジスタンスレベルを更新
        
        Args:
            symbol: 銘柄コード
            ohlc_df: OHLC履歴データ
        """
        try:
            if ohlc_df.empty or len(ohlc_df) < 20:
                logger.warning(f"{symbol}: Insufficient data for level extraction")
                return
            
            # algo4_counter_tradeのレベル抽出を使用
            levels = extract_levels(
                ohlc_df,
                symbol=symbol,
                lookback_bars=config.STRATEGY_PARAMS["lookback_bars"],
                bin_size=config.STRATEGY_PARAMS["bin_size"],
                pivot_left=config.STRATEGY_PARAMS["pivot_left"],
                pivot_right=config.STRATEGY_PARAMS["pivot_right"]
            )
            
            # 強度閾値でフィルタ
            valid_levels = [
                lv for lv in levels 
                if lv.get("strength", 0) >= self.strength_threshold
            ]
            
            self.levels_cache[symbol] = valid_levels
            logger.debug(f"{symbol}: Updated levels, count={len(valid_levels)}")
            
        except Exception as e:
            logger.error(f"Failed to update levels for {symbol}: {e}")
    
    def check_entry_signal(
        self, 
        symbol: str, 
        current_price: float,
        lob_features: Dict[str, float]
    ) -> Optional[Dict[str, Any]]:
        """
        エントリーシグナルをチェック
        
        Args:
            symbol: 銘柄コード
            current_price: 現在価格
            lob_features: LOB特徴量（spread, mid, qi_l1, ofi_20, depth_imb_5等）
        
        Returns:
            シグナル辞書（None: シグナルなし）
            {
                "action": "buy" or "sell",
                "symbol": 銘柄コード,
                "price": エントリー価格,
                "level": 反応したレベル,
                "reason": シグナル理由
            }
        """
        # レベルが存在しない場合はスキップ
        if symbol not in self.levels_cache or not self.levels_cache[symbol]:
            return None
        
        levels = self.levels_cache[symbol]
        
        # 各レベルをチェック
        for lv in levels:
            level_price = lv["level_now"]
            distance = abs(current_price - level_price)
            
            # レベルからの距離がk_tick以内か
            if distance > self.k_tick:
                continue
            
            # 買いシグナル: レベルより下から接近
            if current_price <= level_price + self.k_tick:
                if self._check_reversal_signal(lob_features, "buy"):
                    return {
                        "action": "buy",
                        "symbol": symbol,
                        "price": current_price,
                        "level": level_price,
                        "level_kind": lv.get("kind", "unknown"),
                        "level_strength": lv.get("strength", 0),
                        "reason": f"Buy reversal at support {level_price:.2f}"
                    }
            
            # 売りシグナル: レベルより上から接近
            if current_price >= level_price - self.k_tick:
                if self._check_reversal_signal(lob_features, "sell"):
                    return {
                        "action": "sell",
                        "symbol": symbol,
                        "price": current_price,
                        "level": level_price,
                        "level_kind": lv.get("kind", "unknown"),
                        "level_strength": lv.get("strength", 0),
                        "reason": f"Sell reversal at resistance {level_price:.2f}"
                    }
        
        return None
    
    def _check_reversal_signal(
        self, 
        lob_features: Dict[str, float], 
        direction: str
    ) -> bool:
        """
        リバーサルシグナルをチェック（algo4_counter_tradeロジック）
        
        Args:
            lob_features: LOB特徴量
            direction: "buy" or "sell"
        
        Returns:
            True: リバーサルシグナルあり
        """
        conditions = []
        
        # micro_bias
        micro_bias = lob_features.get("micro_bias", 0)
        if direction == "buy" and micro_bias > 0:
            conditions.append(True)
        elif direction == "sell" and micro_bias < 0:
            conditions.append(True)
        
        # OFI
        ofi = lob_features.get(f"ofi_{config.STRATEGY_PARAMS['roll_n']}", 0)
        if direction == "buy" and ofi > 0:
            conditions.append(True)
        elif direction == "sell" and ofi < 0:
            conditions.append(True)
        
        # QI (Quantity Imbalance)
        qi = lob_features.get("qi_l1", 0)
        if direction == "buy" and qi > 0:
            conditions.append(True)
        elif direction == "sell" and qi < 0:
            conditions.append(True)
        
        # depth_imbalance
        depth_imb = lob_features.get(f"depth_imb_{config.STRATEGY_PARAMS['k_depth']}", 0)
        if direction == "buy" and depth_imb > 0:
            conditions.append(True)
        elif direction == "sell" and depth_imb < 0:
            conditions.append(True)
        
        # いずれか1つ以上満たせばOK
        return len(conditions) > 0 and any(conditions)
    
    def check_exit_signal(
        self,
        position: Dict[str, Any],
        current_price: float,
        hold_bars: int
    ) -> Optional[Dict[str, Any]]:
        """
        決済シグナルをチェック
        
        Args:
            position: ポジション情報
            current_price: 現在価格
            hold_bars: 保有期間（分）
        
        Returns:
            決済シグナル辞書（None: 決済不要）
        """
        entry_price = position["entry_price"]
        direction = position["direction"]
        
        # 損益計算
        if direction == "buy":
            pnl_tick = current_price - entry_price
        else:  # sell
            pnl_tick = entry_price - current_price
        
        # 利確
        if pnl_tick >= config.STRATEGY_PARAMS["x_tick"]:
            return {
                "action": "close",
                "reason": "TP",
                "pnl_tick": pnl_tick
            }
        
        # 損切り
        if pnl_tick <= -config.STRATEGY_PARAMS["y_tick"]:
            return {
                "action": "close",
                "reason": "SL",
                "pnl_tick": pnl_tick
            }
        
        # タイムアウト
        if hold_bars >= config.STRATEGY_PARAMS["max_hold_bars"]:
            return {
                "action": "close",
                "reason": "TO",
                "pnl_tick": pnl_tick
            }
        
        return None


if __name__ == "__main__":
    # テスト用
    logging.basicConfig(
        level=logging.DEBUG,
        format=config.LOGGING_CONFIG["format"]
    )
    
    generator = SignalGenerator()
    
    # ダミーOHLCでレベル更新
    dummy_ohlc = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-22 09:00", periods=100, freq="1min"),
        "open": np.random.randn(100).cumsum() + 1000,
        "high": np.random.randn(100).cumsum() + 1005,
        "low": np.random.randn(100).cumsum() + 995,
        "close": np.random.randn(100).cumsum() + 1000,
        "volume": np.random.randint(1000, 10000, 100)
    })
    generator.update_levels("3350", dummy_ohlc)
    
    # エントリーシグナルチェック
    dummy_lob = {
        "spread": 1.0,
        "mid": 1000.5,
        "micro_bias": 0.1,
        "ofi_20": 100,
        "qi_l1": 0.2,
        "depth_imb_5": 500
    }
    signal = generator.check_entry_signal("3350", 1000.0, dummy_lob)
    print(f"Entry signal: {signal}")
