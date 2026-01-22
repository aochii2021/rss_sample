#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
注文実行・ポジション管理
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd

import config

logger = logging.getLogger(__name__)


class Position:
    """ポジション情報"""
    
    def __init__(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        size: int,
        entry_time: datetime,
        level: float,
        level_kind: str,
        level_strength: float
    ):
        self.symbol = symbol
        self.direction = direction  # "buy" or "sell"
        self.entry_price = entry_price
        self.size = size
        self.entry_time = entry_time
        self.level = level
        self.level_kind = level_kind
        self.level_strength = level_strength
        
        self.exit_price: Optional[float] = None
        self.exit_time: Optional[datetime] = None
        self.pnl_tick: float = 0.0
        self.exit_reason: Optional[str] = None
    
    def close(self, exit_price: float, exit_time: datetime, reason: str):
        """ポジションクローズ"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = reason
        
        if self.direction == "buy":
            self.pnl_tick = exit_price - self.entry_price
        else:
            self.pnl_tick = self.entry_price - exit_price
    
    def get_hold_minutes(self, current_time: datetime) -> int:
        """保有時間（分）を取得"""
        if self.exit_time:
            return int((self.exit_time - self.entry_time).total_seconds() / 60)
        return int((current_time - self.entry_time).total_seconds() / 60)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で返す"""
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time,
            "exit_price": self.exit_price,
            "exit_time": self.exit_time,
            "size": self.size,
            "pnl_tick": self.pnl_tick,
            "exit_reason": self.exit_reason,
            "level": self.level,
            "level_kind": self.level_kind,
            "level_strength": self.level_strength,
        }


class OrderExecutor:
    """注文実行・ポジション管理クラス"""
    
    def __init__(self, dry_run: bool = True):
        """
        Args:
            dry_run: True=シミュレーション、False=実注文
        """
        self.dry_run = dry_run
        self.positions: List[Position] = []  # 現在保有中のポジション
        self.closed_positions: List[Position] = []  # クローズ済みポジション
        
        # リスク管理
        self.daily_pnl_tick = 0.0
        self.consecutive_losses = 0
        self.max_drawdown_tick = 0.0
        self.peak_pnl_tick = 0.0
        
        logger.info(f"OrderExecutor initialized (DRY_RUN={dry_run})")
    
    def can_open_position(self, symbol: str) -> bool:
        """新規ポジションを開けるかチェック"""
        # 最大ポジション数チェック
        if len(self.positions) >= config.RISK_PARAMS["max_positions"]:
            logger.debug("Max positions reached")
            return False
        
        # 1銘柄あたりの最大ポジション数チェック
        symbol_positions = [p for p in self.positions if p.symbol == symbol]
        if len(symbol_positions) >= config.RISK_PARAMS["max_position_per_symbol"]:
            logger.debug(f"{symbol}: Max positions per symbol reached")
            return False
        
        # 1日の最大損失チェック
        if self.daily_pnl_tick <= -config.RISK_PARAMS["max_daily_loss_tick"]:
            logger.warning(f"Daily loss limit reached: {self.daily_pnl_tick:.2f} tick")
            return False
        
        # 緊急停止条件チェック
        if self.consecutive_losses >= config.RISK_PARAMS["emergency_stop"]["consecutive_losses"]:
            logger.warning(f"Emergency stop: {self.consecutive_losses} consecutive losses")
            return False
        
        if self.max_drawdown_tick >= config.RISK_PARAMS["emergency_stop"]["drawdown_tick"]:
            logger.warning(f"Emergency stop: drawdown {self.max_drawdown_tick:.2f} tick")
            return False
        
        return True
    
    def open_position(self, signal: Dict[str, Any]) -> bool:
        """
        ポジションを開く
        
        Args:
            signal: エントリーシグナル
        
        Returns:
            True: 成功、False: 失敗
        """
        symbol = signal["symbol"]
        
        if not self.can_open_position(symbol):
            return False
        
        try:
            # 注文実行
            if self.dry_run:
                logger.info(f"[DRY RUN] Opening {signal['action']} position: {symbol} @ {signal['price']:.2f}")
                success = True
            else:
                # TODO: 実際の注文実行（MarketSpeed II経由）
                logger.info(f"[LIVE] Opening {signal['action']} position: {symbol} @ {signal['price']:.2f}")
                success = self._execute_order(signal)
            
            if success:
                # ポジション作成
                position = Position(
                    symbol=symbol,
                    direction=signal["action"],
                    entry_price=signal["price"],
                    size=config.RISK_PARAMS["position_size"],
                    entry_time=datetime.now(),
                    level=signal["level"],
                    level_kind=signal.get("level_kind", "unknown"),
                    level_strength=signal.get("level_strength", 0.0)
                )
                self.positions.append(position)
                
                logger.info(f"Position opened: {symbol} {signal['action']} @ {signal['price']:.2f}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to open position: {e}")
        
        return False
    
    def close_position(self, position: Position, current_price: float, reason: str) -> bool:
        """
        ポジションをクローズ
        
        Args:
            position: クローズするポジション
            current_price: 現在価格
            reason: クローズ理由
        
        Returns:
            True: 成功、False: 失敗
        """
        try:
            # 注文実行
            if self.dry_run:
                logger.info(f"[DRY RUN] Closing position: {position.symbol} @ {current_price:.2f} ({reason})")
                success = True
            else:
                # TODO: 実際の注文実行
                logger.info(f"[LIVE] Closing position: {position.symbol} @ {current_price:.2f} ({reason})")
                success = self._execute_close_order(position, current_price)
            
            if success:
                # ポジションクローズ
                position.close(current_price, datetime.now(), reason)
                
                # 損益更新
                self.daily_pnl_tick += position.pnl_tick
                self.peak_pnl_tick = max(self.peak_pnl_tick, self.daily_pnl_tick)
                self.max_drawdown_tick = self.peak_pnl_tick - self.daily_pnl_tick
                
                # 連続損失カウント
                if position.pnl_tick < 0:
                    self.consecutive_losses += 1
                else:
                    self.consecutive_losses = 0
                
                # ポジションリストから削除
                self.positions.remove(position)
                self.closed_positions.append(position)
                
                logger.info(
                    f"Position closed: {position.symbol} "
                    f"PnL={position.pnl_tick:.2f} tick ({reason}), "
                    f"Daily PnL={self.daily_pnl_tick:.2f} tick"
                )
                return True
            
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
        
        return False
    
    def _execute_order(self, signal: Dict[str, Any]) -> bool:
        """実際の注文実行（MarketSpeed II）"""
        # TODO: MarketSpeed II RSSを使った注文実行を実装
        logger.warning("_execute_order: Not implemented (MarketSpeed II integration required)")
        return True
    
    def _execute_close_order(self, position: Position, price: float) -> bool:
        """実際のクローズ注文実行"""
        # TODO: MarketSpeed II RSSを使った注文実行を実装
        logger.warning("_execute_close_order: Not implemented (MarketSpeed II integration required)")
        return True
    
    def get_open_positions(self) -> List[Position]:
        """保有中のポジションを取得"""
        return self.positions.copy()
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """本日の統計を取得"""
        total_trades = len(self.closed_positions)
        wins = sum(1 for p in self.closed_positions if p.pnl_tick > 0)
        
        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": total_trades - wins,
            "win_rate": wins / total_trades if total_trades > 0 else 0.0,
            "daily_pnl_tick": self.daily_pnl_tick,
            "max_drawdown_tick": self.max_drawdown_tick,
            "consecutive_losses": self.consecutive_losses,
            "open_positions": len(self.positions),
        }
    
    def save_logs(self, date_str: str):
        """ログをCSV保存"""
        if not self.closed_positions:
            return
        
        # ポジションログ
        positions_data = [p.to_dict() for p in self.closed_positions]
        positions_df = pd.DataFrame(positions_data)
        
        log_path = str(config.LOGGING_CONFIG["position_log"]).format(date=date_str)
        positions_df.to_csv(log_path, index=False)
        logger.info(f"Saved position log: {log_path}")


if __name__ == "__main__":
    # テスト用
    logging.basicConfig(
        level=logging.DEBUG,
        format=config.LOGGING_CONFIG["format"]
    )
    
    executor = OrderExecutor(dry_run=True)
    
    # ダミーシグナルでポジションを開く
    dummy_signal = {
        "action": "buy",
        "symbol": "3350",
        "price": 1000.0,
        "level": 995.0,
        "level_kind": "vpoc",
        "level_strength": 0.8,
        "reason": "Test signal"
    }
    
    executor.open_position(dummy_signal)
    
    # 統計表示
    stats = executor.get_daily_stats()
    print(f"Daily stats: {stats}")
    
    # ポジションクローズ
    if executor.positions:
        executor.close_position(executor.positions[0], 1010.0, "TP")
        stats = executor.get_daily_stats()
        print(f"After close: {stats}")
