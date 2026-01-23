#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
注文実行・ポジション管理
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd
import win32com.client

import config
from rss_functions import RSSFunctions

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
        
        # pending注文管理（約定待ちリスト）
        self.pending_orders: List[Dict[str, Any]] = []
        self.order_id_counter = 0  # 注文IDカウンター（衝突回避）
        
        # Excel COM接続（DRY_RUN=Falseの場合）- 注文実行専用
        self.excel_order = None
        self.rss = None
        if not dry_run:
            try:
                self.excel_order = win32com.client.Dispatch("Excel.Application")
                self.excel_order.Visible = True
                self.rss = RSSFunctions(self.excel_order)
                logger.info("Excel COM connection established (Order Execution)")
            except Exception as e:
                logger.error(f"Failed to connect to Excel: {e}")
                raise
        
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
        """
        信用新規注文実行（MarketSpeed II RSS）
        
        Args:
            signal: エントリーシグナル（symbol, action, price等）
        
        Returns:
            True: 注文成功、False: 注文失敗
        """
        if not self.excel:
            logger.error("Excel not connected")
            return False
        
        try:
            symbol = signal["symbol"]
            action = signal["action"]  # "buy" or "sell"
            price = signal["price"]
            
            # 発注IDを生成（マイクロ秒+カウンター方式、衝突回避）
            self.order_id_counter += 1
            timestamp_part = int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])
            order_id = timestamp_part + self.order_id_counter
            
            # 売買区分: 1=売建、3=買建
            trade_type = "3" if action == "buy" else "1"
            
            # 注文パラメータ
            order_params = [
                order_id,                                      # 1. 発注ID
                1,                                             # 2. 発注トリガー（1=発注）
                f"{symbol}.T",                                # 3. 銘柄コード（東証）
                trade_type,                                    # 4. 売買区分（1=売建、3=買建）
                "0",                                          # 5. 注文区分（0=通常注文）
                "0",                                          # 6. SOR区分（0=通常）
                config.MARGIN_PARAMS["margin_type"],         # 7. 信用区分
                config.RISK_PARAMS["position_size"],          # 8. 注文数量
                "1",                                          # 9. 価格区分（1=指値）
                price,                                         # 10. 注文価格
                "1",                                          # 11. 執行条件（1=本日中）
                "",                                           # 12. 注文期限（本日中なので省略）
                config.MARGIN_PARAMS["account_type"],        # 13. 口座区分
            ]
            
            # RssMarginOpenOrder関数を呼び出し
            result = self.excel_order.Run("RssMarginOpenOrder", *order_params)
            
            if result:
                logger.info(
                    f"Order sent: {symbol} {action} {config.RISK_PARAMS['position_size']}株 @ {price:.2f} "
                    f"(OrderID: {order_id})"
                )
                
                # pending注文リストに追加（約定待ち）
                self.pending_orders.append({
                    "order_id": order_id,
                    "signal": signal,
                    "timestamp": datetime.now(),
                    "order_type": "open"
                })
                logger.debug(f"Added to pending orders: {order_id}")
                return True
            else:
                logger.error(f"Order failed: {symbol} {action} @ {price:.2f}")
                return False
                
        except Exception as e:
            logger.error(f"Order execution error: {e}")
            return False
    
    def _execute_close_order(self, position: Position, price: float) -> bool:
        """
        信用返済注文実行（MarketSpeed II RSS）
        
        Args:
            position: クローズするポジション
            price: 返済価格
        
        Returns:
            True: 注文成功、False: 注文失敗
        """
        if not self.excel:
            logger.error("Excel not connected")
            return False
        
        try:
            symbol = position.symbol
            direction = position.direction
            
            # 発注IDを生成（マイクロ秒+カウンター方式）
            self.order_id_counter += 1
            timestamp_part = int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])
            order_id = timestamp_part + self.order_id_counter
            
            # 売買区分: 1=売埋、3=買埋（新規と逆）
            trade_type = "1" if direction == "buy" else "3"
            
            # 建日（ポジション建てた日）
            entry_date = position.entry_time.strftime("%Y%m%d")
            
            # 注文パラメータ
            order_params = [
                order_id,                                      # 1. 発注ID
                1,                                             # 2. 発注トリガー（1=発注）
                f"{symbol}.T",                                # 3. 銘柄コード（東証）
                trade_type,                                    # 4. 売買区分（1=売埋、3=買埋）
                "0",                                          # 5. 注文区分（0=通常注文）
                "0",                                          # 6. SOR区分（0=通常）
                config.MARGIN_PARAMS["margin_type"],         # 7. 信用区分
                position.size,                                 # 8. 注文数量
                "1",                                          # 9. 価格区分（1=指値）
                price,                                         # 10. 注文価格
                "1",                                          # 11. 執行条件（1=本日中）
                "",                                           # 12. 注文期限（本日中なので省略）
                config.MARGIN_PARAMS["account_type"],        # 13. 口座区分
                entry_date,                                    # 14. 建日
                position.entry_price,                          # 15. 建単価
                "1",                                          # 16. 建市場（1=東証）
            ]
            
            # RssMarginCloseOrder関数を呼び出し
            result = self.excel_order.Run("RssMarginCloseOrder", *order_params)
            
            if result:
                logger.info(
                    f"Close order sent: {symbol} {position.size}株 @ {price:.2f} "
                    f"(OrderID: {order_id}, Entry: {position.entry_price:.2f})"
                )
                
                # pending注文リストに追加（約定待ち）
                self.pending_orders.append({
                    "order_id": order_id,
                    "position": position,
                    "price": price,
                    "reason": reason,
                    "timestamp": datetime.now(),
                    "order_type": "close"
                })
                logger.debug(f"Added to pending close orders: {order_id}")
                return True
            else:
                logger.error(f"Close order failed: {symbol} @ {price:.2f}")
                return False
                
        except Exception as e:
            logger.error(f"Close order execution error: {e}")
            return False
    
    def get_open_positions(self) -> List[Position]:
        """保有中のポジションを取得"""
        return self.positions.copy()
    
    def check_pending_orders(self):
        """
        pending注文の約定状況をチェックし、約定済みならポジション作成/クローズ
        
        Returns:
            処理済み注文数
        """
        if not self.rss:
            return 0
        
        processed_count = 0
        
        for pending in self.pending_orders[:]:
            order_id = pending["order_id"]
            elapsed_sec = (datetime.now() - pending["timestamp"]).total_seconds()
            
            # 設定値のタイムアウトで判定
            timeout_sec = config.RSS_PARAMS["pending_order_timeout_sec"]
            if elapsed_sec > timeout_sec:
                logger.error(
                    f"Order {order_id} timeout ({timeout_sec}s elapsed), "
                    f"type={pending['order_type']}, status={self.rss.get_order_status(order_id)}"
                )
                self.pending_orders.remove(pending)
                processed_count += 1
                continue
            
            # 約定確認（タイムアウトは設定値）
            check_timeout = config.RSS_PARAMS["order_filled_check_timeout_sec"]
            if self.rss.check_order_filled(order_id, timeout_sec=check_timeout):
                if pending["order_type"] == "open":
                    # 新規注文約定→Positionオブジェクト作成
                    signal = pending["signal"]
                    position = Position(
                        symbol=signal["symbol"],
                        direction=signal["action"],
                        entry_price=signal["price"],
                        size=config.RISK_PARAMS["position_size"],
                        entry_time=datetime.now(),
                        level=signal["level"],
                        level_kind=signal.get("level_kind", "unknown"),
                        level_strength=signal.get("level_strength", 0.0)
                    )
                    self.positions.append(position)
                    logger.info(
                        f"Position opened (filled): {signal['symbol']} {signal['action']} @ {signal['price']:.2f} "
                        f"(OrderID: {order_id})"
                    )
                
                elif pending["order_type"] == "close":
                    # 決済注文約定→ポジションクローズ
                    position = pending["position"]
                    price = pending["price"]
                    reason = pending["reason"]
                    
                    position.close(price, datetime.now(), reason)
                    
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
                    if position in self.positions:
                        self.positions.remove(position)
                    self.closed_positions.append(position)
                    
                    logger.info(
                        f"Position closed (filled): {position.symbol} "
                        f"PnL={position.pnl_tick:.2f} tick ({reason}), "
                        f"Daily PnL={self.daily_pnl_tick:.2f} tick (OrderID: {order_id})"
                    )
                
                self.pending_orders.remove(pending)
                processed_count += 1
        
        if processed_count > 0:
            logger.debug(f"Processed {processed_count} pending orders")
        
        return processed_count
    
    def sync_positions_with_rss(self) -> Dict[str, Any]:
        """
        RSS建玉一覧とローカルポジションを照合
        
        Returns:
            照合結果Dict（rss_count, local_count, matched, missing_in_local, missing_in_rss）
        """
        if not self.rss:
            return {"error": "RSS not available in DRY_RUN mode"}
        
        try:
            # RSS建玉一覧を取得
            rss_positions = self.rss.get_margin_positions(
                account_type=config.MARGIN_PARAMS["account_type"],
                margin_type=config.MARGIN_PARAMS["margin_type"]
            )
            
            result = {
                "rss_count": len(rss_positions),
                "local_count": len(self.positions),
                "matched": 0,
                "missing_in_local": [],
                "missing_in_rss": []
            }
            
            # ローカルポジションの銘柄リスト
            local_symbols = {p.symbol for p in self.positions}
            
            # RSS建玉の銘柄リスト
            if not rss_positions.empty and "銘柄コード" in rss_positions.columns:
                rss_symbols = set(rss_positions["銘柄コード"].astype(str))
                
                # 一致数
                result["matched"] = len(local_symbols & rss_symbols)
                
                # ローカルにないがRSSにある
                result["missing_in_local"] = list(rss_symbols - local_symbols)
                
                # RSSにないがローカルにある
                result["missing_in_rss"] = list(local_symbols - rss_symbols)
            else:
                result["missing_in_rss"] = list(local_symbols)
            
            if result["missing_in_local"] or result["missing_in_rss"]:
                logger.warning(f"Position mismatch: {result}")
            else:
                logger.info(f"Positions synced: {result['matched']} matched")
            
            return result
            
        except Exception as e:
            logger.error(f"Error syncing positions: {e}")
            return {"error": str(e)}
    
    def __del__(self):
        """デストラクタでExcelをクリーンアップ"""
        if self.excel_order:
            try:
                self.excel_order.Quit()
                logger.info("Excel COM connection closed (Order Execution)")
            except Exception as e:
                logger.error(f"Error closing Excel: {e}")
    
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
