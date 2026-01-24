#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
逆張り（カウンタートレード）戦略ロジック

バックテストとライブ取引の両方で使用可能な戦略クラス。
LOB特徴量とS/Rレベルを用いた反転検知ロジックを実装。
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """ポジション情報"""
    entry_idx: int
    entry_price: float
    entry_ts: datetime
    direction: str  # 'buy' or 'sell'
    level: float
    level_strength: float
    level_count: int
    symbol: str


@dataclass
class ExitSignal:
    """決済シグナル"""
    should_exit: bool
    reason: str
    pnl_tick: float


class CounterTradeStrategy:
    """
    逆張り戦略クラス
    
    S/Rレベル近辺での反転を狙う戦略。
    LOB特徴量（micro_bias, OFI, QI, depth_imb）を用いて反転シグナルを検出。
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: パラメータ辞書
                - k_tick: レベル反応帯の幅
                - x_tick: 利確幅
                - y_tick: 損切幅
                - max_hold_bars: 最大保有時間
                - strength_th: レベル強度閾値
                - roll_n: OFI/depth_imb計算用ローリング期間
                - k_depth: depth_imb計算用板深さ
        """
        self.k_tick = params.get('k_tick', 5.0)
        self.x_tick = params.get('x_tick', 10.0)
        self.y_tick = params.get('y_tick', 5.0)
        self.max_hold_bars = params.get('max_hold_bars', 60)
        self.strength_th = params.get('strength_th', 0.5)
        self.roll_n = params.get('roll_n', 20)
        self.k_depth = params.get('k_depth', 5)
        
        # カラム名
        self.micro_bias_col = "micro_bias"
        self.ofi_col = f"ofi_{self.roll_n}"
        self.qi_col = "qi_l1"
        self.depth_col = f"depth_imb_{self.k_depth}"
        
        logger.info(f"Strategy initialized: k={self.k_tick}, x={self.x_tick}, "
                   f"y={self.y_tick}, max_hold={self.max_hold_bars}")
    
    def is_near_level(self, price: float, level: float) -> bool:
        """価格がレベルの反応帯内か判定"""
        return abs(price - level) <= self.k_tick
    
    def check_entry_signal(
        self,
        row: pd.Series,
        level: float,
        direction: str
    ) -> bool:
        """
        エントリーシグナルのチェック
        
        Args:
            row: 現在のLOBデータ行
            level: レベル価格
            direction: 'buy' または 'sell'
            
        Returns:
            エントリー可能な場合True
        """
        price = row['mid']
        
        # 価格がレベル反応帯内か確認
        if not self.is_near_level(price, level):
            return False
        
        # 買いエントリー: レベルの上側から下に接近
        if direction == 'buy' and price > level + self.k_tick:
            return False
        
        # 売りエントリー: レベルの下側から上に接近
        if direction == 'sell' and price < level - self.k_tick:
            return False
        
        # 反転シグナルの確認
        return self.check_reversal_signal(row, direction)
    
    def check_reversal_signal(
        self,
        row: pd.Series,
        direction: str
    ) -> bool:
        """
        反転シグナルのチェック
        
        Args:
            row: 現在のLOBデータ行
            direction: 'buy'（下から戻り）または 'sell'（上から戻り）
            
        Returns:
            反転シグナルがある場合True（いずれか1つ以上満たす）
        """
        conditions = []
        
        # micro_bias: 買いなら正、売りなら負
        if self.micro_bias_col in row.index and not pd.isna(row[self.micro_bias_col]):
            if direction == "buy" and row[self.micro_bias_col] > 0:
                conditions.append(True)
            elif direction == "sell" and row[self.micro_bias_col] < 0:
                conditions.append(True)
        
        # OFI: 買いなら正、売りなら負
        if self.ofi_col in row.index and not pd.isna(row[self.ofi_col]):
            if direction == "buy" and row[self.ofi_col] > 0:
                conditions.append(True)
            elif direction == "sell" and row[self.ofi_col] < 0:
                conditions.append(True)
        
        # QI: 買いなら正、売りなら負
        if self.qi_col in row.index and not pd.isna(row[self.qi_col]):
            if direction == "buy" and row[self.qi_col] > 0:
                conditions.append(True)
            elif direction == "sell" and row[self.qi_col] < 0:
                conditions.append(True)
        
        # depth_imb: 買いなら正、売りなら負
        if self.depth_col in row.index and not pd.isna(row[self.depth_col]):
            if direction == "buy" and row[self.depth_col] > 0:
                conditions.append(True)
            elif direction == "sell" and row[self.depth_col] < 0:
                conditions.append(True)
        
        # いずれか1つ以上満たせばTrue
        return len(conditions) > 0 and any(conditions)
    
    def check_exit_signal(
        self,
        position: Position,
        row: pd.Series,
        current_idx: int,
        lob_df: pd.DataFrame,
        levels: List[Dict[str, Any]]
    ) -> ExitSignal:
        """
        決済シグナルのチェック
        
        Args:
            position: 保有ポジション
            row: 現在のLOBデータ行
            current_idx: 現在のインデックス
            lob_df: LOBデータ全体（急落検知用）
            levels: レベルリスト（レジスタンス検知用）
            
        Returns:
            ExitSignal
        """
        price = row['mid']
        hold_bars = current_idx - position.entry_idx
        
        # 損益計算
        if position.direction == 'buy':
            pnl_tick = price - position.entry_price
        else:
            pnl_tick = position.entry_price - price
        
        # 1. 基本的な利確・損切
        if pnl_tick >= self.x_tick:
            return ExitSignal(True, "TP", pnl_tick)
        
        if pnl_tick <= -self.y_tick:
            return ExitSignal(True, "SL", pnl_tick)
        
        if hold_bars >= self.max_hold_bars:
            return ExitSignal(True, "TO", pnl_tick)
        
        # 2. 含み益がある場合の動的利確
        if pnl_tick > 0:
            # 2-1. 半値戻しでの利確
            has_drop, high_price, low_price, drop_size = self.detect_recent_drop(
                lob_df, current_idx, lookback=10
            )
            if has_drop and position.direction == 'buy':
                half_retracement = low_price + (drop_size * 0.5)
                if price >= half_retracement and pnl_tick >= 5.0:
                    return ExitSignal(True, "HALF_RETRACE", pnl_tick)
            
            # 2-2. 次のレジスタンス接近での利確
            next_resistance = self.find_next_resistance(
                price, position.direction, levels
            )
            if next_resistance is not None:
                distance = abs(price - next_resistance)
                if distance <= 1.5 and pnl_tick >= 8.0:
                    return ExitSignal(True, "NEAR_RESISTANCE", pnl_tick)
            
            # 2-3. 反発が弱まっている場合の早期利確
            if hold_bars >= 5:
                if self.is_reversal_weakening(row, position.direction):
                    if pnl_tick >= 5.0:
                        return ExitSignal(True, "WEAK_REVERSAL", pnl_tick)
        
        # 3. 含み損時の早期損切り
        elif pnl_tick < 0 and hold_bars >= 2:
            if self.is_reversal_failing(row, position.direction):
                if -1.5 <= pnl_tick <= -self.y_tick:
                    return ExitSignal(True, "EARLY_SL", pnl_tick)
        
        return ExitSignal(False, "", pnl_tick)
    
    def detect_recent_drop(
        self,
        lob_df: pd.DataFrame,
        current_idx: int,
        lookback: int = 10
    ) -> Tuple[bool, float, float, float]:
        """
        直近の急落を検出
        
        Returns:
            (has_drop, high_price, low_price, drop_size)
        """
        if current_idx < lookback:
            return False, 0.0, 0.0, 0.0
        
        recent_slice = lob_df.iloc[max(0, current_idx - lookback):current_idx + 1]
        if len(recent_slice) < 2:
            return False, 0.0, 0.0, 0.0
        
        high_price = recent_slice['mid'].max()
        low_price = recent_slice['mid'].min()
        drop_size = high_price - low_price
        
        # 直近の最安値が現在から3本以内にある場合は「急落中」とみなす
        low_idx = recent_slice['mid'].idxmin()
        bars_since_low = current_idx - low_idx
        
        # 急落判定：下落幅が大きく、かつ最安値が最近
        has_drop = drop_size > 7.0 and bars_since_low <= 3
        
        return has_drop, high_price, low_price, drop_size
    
    def find_next_resistance(
        self,
        price: float,
        direction: str,
        levels: List[Dict[str, Any]]
    ) -> Optional[float]:
        """
        次のレジスタンスレベルを検索
        
        Args:
            price: 現在価格
            direction: "buy" または "sell"
            levels: レベルリスト
            
        Returns:
            次のレジスタンス価格（見つからない場合はNone）
        """
        if direction == "buy":
            # 買いポジション：現在価格より上のレベル
            upper_levels = [lv['level_now'] for lv in levels if lv['level_now'] > price]
            if upper_levels:
                return min(upper_levels)
        else:
            # 売りポジション：現在価格より下のレベル
            lower_levels = [lv['level_now'] for lv in levels if lv['level_now'] < price]
            if lower_levels:
                return max(lower_levels)
        
        return None
    
    def is_reversal_weakening(
        self,
        row: pd.Series,
        direction: str
    ) -> bool:
        """
        反発が弱まっているか判定
        
        Args:
            row: 現在の行データ
            direction: "buy" または "sell"
            
        Returns:
            反発が弱まっている場合True
        """
        ofi = row.get(self.ofi_col, 0)
        depth_imb = row.get(self.depth_col, 0)
        
        if direction == "buy":
            # 買いポジション：OFIが負（売り圧力）、depth_imbが負（売り板厚い）
            return ofi < -0.3 and depth_imb < -0.2
        else:
            # 売りポジション：OFIが正（買い圧力）、depth_imbが正（買い板厚い）
            return ofi > 0.3 and depth_imb > 0.2
    
    def is_reversal_failing(
        self,
        row: pd.Series,
        direction: str
    ) -> bool:
        """
        反転シグナルが消失しているか判定（含み損時の早期損切り用）
        
        Args:
            row: 現在の行データ
            direction: "buy" または "sell"
            
        Returns:
            反転が失敗している（逆方向の圧力が強い）場合True
        """
        micro_bias = row.get(self.micro_bias_col, 0)
        ofi = row.get(self.ofi_col, 0)
        depth_imb = row.get(self.depth_col, 0)
        
        if direction == "buy":
            # 買いポジションで含み損：下落圧力が強い = 反転失敗
            has_sell_pressure = ofi < -0.2 or depth_imb < -0.15
            if micro_bias < -0.2 and has_sell_pressure:
                return True
            return ofi < -0.15 and depth_imb < -0.15
        else:
            # 売りポジションで含み損：上昇圧力が強い = 反転失敗
            has_buy_pressure = ofi > 0.2 or depth_imb > 0.15
            if micro_bias > 0.2 and has_buy_pressure:
                return True
            return ofi > 0.15 and depth_imb > 0.15
    
    def get_trading_session(self, ts: datetime) -> str:
        """
        取引セッションを判定
        
        Args:
            ts: タイムスタンプ
            
        Returns:
            'morning': 前場 (9:00-11:30)
            'afternoon': 後場 (12:30-15:15)
            'closed': 場外
        """
        if not hasattr(ts, 'hour'):
            return 'closed'
        
        hour = ts.hour
        minute = ts.minute
        
        # 前場: 9:00 - 11:30
        if (hour == 9 and minute >= 0) or (hour == 10) or (hour == 11 and minute <= 30):
            return 'morning'
        
        # 後場: 12:30 - 15:15
        if (hour == 12 and minute >= 30) or (hour == 13) or (hour == 14) or (hour == 15 and minute <= 15):
            return 'afternoon'
        
        return 'closed'
    
    def is_session_end_approaching(
        self,
        ts: datetime,
        session: str,
        minutes_before: int = 5
    ) -> bool:
        """
        セッション終了が近づいているか判定
        
        Args:
            ts: タイムスタンプ
            session: セッション ('morning' or 'afternoon')
            minutes_before: 何分前から判定するか
            
        Returns:
            セッション終了間近の場合True
        """
        if not hasattr(ts, 'hour'):
            return False
        
        hour = ts.hour
        minute = ts.minute
        
        if session == 'morning':
            # 11:30の5分前 = 11:25
            return hour == 11 and minute >= (30 - minutes_before)
        elif session == 'afternoon':
            # 15:15の5分前 = 15:10
            return hour == 15 and minute >= (15 - minutes_before)
        
        return False
