#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
実トレードメインプログラム
algo4_counter_tradeの逆張り戦略を実行
"""
import sys
import time
import logging
from datetime import datetime, time as dt_time
from pathlib import Path
import pandas as pd
import win32com.client
from typing import Protocol, Any, List, Dict, Optional

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from live_data_collector import LiveDataCollector
from core.strategy import CounterTradeStrategy
from core.level_generator import LevelGenerator
from order_executor import OrderExecutor

# ロギング設定（ログディレクトリ自動作成）
config.LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = str(config.LOGGING_CONFIG["trade_log"]).format(date=datetime.now().strftime("%Y%m%d"))
logging.basicConfig(
    level=getattr(logging, config.LOGGING_CONFIG["level"]),
    format=config.LOGGING_CONFIG["format"],
    datefmt=config.LOGGING_CONFIG["date_format"],
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IStrategy(Protocol):
    def check_entry(self, current_bar: pd.Series, levels: List[Any]) -> Optional[Dict]: ...
    def check_exit(self, position: Any, current_bar: pd.Series) -> Optional[Dict]: ...

class ILevelGenerator(Protocol):
    def generate(self, symbol: str, ohlc_df: pd.DataFrame) -> List[Any]: ...

class IDataCollector(Protocol):
    def update(self) -> Dict[str, Dict]: ...
    def get_history(self, symbol: str, lookback_bars: int) -> pd.DataFrame: ...

class IOrderExecutor(Protocol):
    def open_position(self, entry_info: Dict): ...
    def close_position(self, position: Any, price: float, reason: str): ...
    def get_open_positions(self) -> List[Any]: ...
    def check_pending_orders(self): ...
    def get_daily_stats(self) -> Dict[str, Any]: ...
    def sync_positions_with_rss(self) -> Dict[str, Any]: ...
    def save_logs(self, date_str: str): ...


class TradingSystem:
    """実トレードシステム（抽象インターフェース依存）"""
    def __init__(self,
                 strategy: IStrategy,
                 level_generator: ILevelGenerator,
                 data_collector: IDataCollector,
                 order_executor: IOrderExecutor):
        self.symbols = self._load_symbols()
        logger.info(f"Target symbols: {len(self.symbols)}")
        self.strategy = strategy
        self.level_generator = level_generator
        self.data_collector = data_collector
        self.order_executor = order_executor
        self.is_running = False
        self.current_session = None
        self.last_position_sync = datetime.now()
        logger.info("TradingSystem initialized (interface-based)")

    def _load_symbols(self) -> list:
        """対象銘柄を読み込み"""
        if config.TARGET_SYMBOLS:
            return config.TARGET_SYMBOLS
        
        # watchlistから読み込み
        try:
            watchlist_df = pd.read_csv(config.RSS_PARAMS["watchlist_path"])
            symbols = watchlist_df["コード"].astype(str).tolist()
            return symbols
        except Exception as e:
            logger.error(f"Failed to load watchlist: {e}")
            return []
    
    def __del__(self):
        """デストラクタでリソースをクリーンアップ"""
        if self.excel_data:
            try:
                self.excel_data.Quit()
                logger.info("Excel COM connection closed (Data Collection)")
            except Exception as e:
                logger.error(f"Error closing Excel (Data): {e}")
    
    def _is_trading_session(self) -> bool:
        """現在が取引時間内かチェック"""
        now = datetime.now().time()
        
        for session_name, (start_str, end_str) in config.RISK_PARAMS["trading_sessions"].items():
            start_time = dt_time.fromisoformat(start_str)
            end_time = dt_time.fromisoformat(end_str)
            
            if start_time <= now <= end_time:
                if self.current_session != session_name:
                    self.current_session = session_name
                    logger.info(f"Entered {session_name} session")
                return True
        
        if self.current_session:
            logger.info(f"Exited {self.current_session} session")
            self.current_session = None
        
        return False
    
    def _update_data_and_levels(self):
        """データ更新とレベル更新"""
        lob_data = self.data_collector.update()
        
        for symbol in self.symbols:
            ohlc_history = self.data_collector.get_history(
                symbol,
                lookback_bars=self.strategy_params["lookback_bars"]
            )
            
            if not ohlc_history.empty:
                # OHLCデータ生成
                ohlc_df = pd.DataFrame({
                    "timestamp": ohlc_history["ts"],
                    "open": ohlc_history["mid"],
                    "high": ohlc_history["mid"],
                    "low": ohlc_history["mid"],
                    "close": ohlc_history["mid"],
                    "volume": 0
                })
                
                # レベル生成
                levels = self.level_generator.generate(symbol, ohlc_df)
                # レベル情報を戦略にセット
                # self.strategy.set_levels(symbol, levels) # 必要に応じて
    
    def _check_signals(self, lob_data: dict):
        """シグナルチェックと注文実行"""
        current_time = datetime.now()
        
        # pending注文の約定確認（毎ループ）
        self.order_executor.check_pending_orders()
        
        # 新規エントリーチェック
        for symbol, lob_features in lob_data.items():
            current_price = lob_features.get("mid", 0)
            if current_price == 0:
                continue
            
            # レベル情報取得（仮: self.level_generatorから取得）
            levels = [] # TODO: 実装に合わせて取得
            for level in levels:
                for direction in ["buy", "sell"]:
                    if self.strategy.check_entry_signal(pd.Series(lob_features), level, direction):
                        logger.info(f"Entry signal: {symbol} {direction} @ {level}")
                        self.order_executor.open_position({
                            "symbol": symbol,
                            "direction": direction,
                            "entry_price": current_price,
                            "level": level
                        })
        
        # 保有ポジションの決済チェック
        for position in self.order_executor.get_open_positions():
            # 現在価格を取得
            if position.symbol not in lob_data:
                continue
            
            current_price = lob_data[position.symbol].get("mid", 0)
            if current_price == 0:
                continue
            
            # 保有時間
            hold_bars = position.get_hold_minutes(current_time)
            
            # 決済シグナルチェック
            exit_signal = self.signal_generator.check_exit_signal(
                position.to_dict(),
                current_price,
                hold_bars
            )
            
            if exit_signal:
                logger.info(f"Exit signal: {exit_signal}")
                self.order_executor.close_position(
                    position,
                    current_price,
                    exit_signal["reason"]
                )
        
        # 1分ごとにポジション照合
        if (datetime.now() - self.last_position_sync).total_seconds() >= 60:
            sync_result = self.order_executor.sync_positions_with_rss()
            if sync_result.get("missing_in_rss"):
                logger.critical(f"Missing positions in RSS: {sync_result['missing_in_rss']}")
            if sync_result.get("missing_in_local"):
                logger.critical(f"Missing positions in local: {sync_result['missing_in_local']}")
            self.last_position_sync = datetime.now()
    
    def _session_end_close_all(self):
        """セッション終了時に全ポジションクローズ"""
        logger.info("Session ending, closing all positions...")
        
        for position in self.order_executor.get_open_positions():
            # 最終価格で強制クローズ
            # TODO: 実際の市場価格を取得
            logger.warning(f"Force closing {position.symbol} (session end)")
            self.order_executor.close_position(
                position,
                position.entry_price,  # 暫定: エントリー価格
                "SESSION_END"
            )
    
    def run(self):
        """メインループ実行"""
        self.is_running = True
        logger.info("=" * 50)
        logger.info("Trading system started")
        logger.info(f"DRY_RUN: {config.DRY_RUN}")
        logger.info(f"Symbols: {len(self.symbols)}")
        logger.info("=" * 50)
        
        last_session_active = False
        
        try:
            while self.is_running:
                # 取引時間チェック
                in_session = self._is_trading_session()
                
                if in_session:
                    # データ更新とレベル更新
                    self._update_data_and_levels()
                    
                    # リアルタイムデータ取得
                    lob_data = self.data_collector.update()
                    
                    # シグナルチェックと注文実行
                    self._check_signals(lob_data)
                    
                    # 統計表示
                    stats = self.order_executor.get_daily_stats()
                    logger.info(
                        f"Stats: Trades={stats['total_trades']}, "
                        f"WinRate={stats['win_rate']:.1%}, "
                        f"PnL={stats['daily_pnl_tick']:.2f} tick, "
                        f"Open={stats['open_positions']}"
                    )
                    
                    last_session_active = True
                    
                else:
                    # セッション終了直後の処理
                    if last_session_active:
                        self._session_end_close_all()
                        last_session_active = False
                    
                    # 取引時間外は待機
                    logger.debug("Outside trading hours, waiting...")
                
                # 更新間隔待機
                time.sleep(config.RSS_PARAMS["update_interval_sec"])
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """システム停止"""
        logger.info("Stopping trading system...")
        self.is_running = False
        
        # 全ポジションクローズ
        if self.order_executor.get_open_positions():
            logger.warning("Closing all open positions...")
            self._session_end_close_all()
        
        # ログ保存
        date_str = datetime.now().strftime("%Y%m%d")
        self.order_executor.save_logs(date_str)
        
        # 統計表示
        stats = self.order_executor.get_daily_stats()
        logger.info("=" * 50)
        logger.info("Trading session summary:")
        logger.info(f"  Total trades: {stats['total_trades']}")
        logger.info(f"  Wins: {stats['wins']}")
        logger.info(f"  Losses: {stats['losses']}")
        logger.info(f"  Win rate: {stats['win_rate']:.1%}")
        logger.info(f"  Daily PnL: {stats['daily_pnl_tick']:.2f} tick")
        logger.info(f"  Max DD: {stats['max_drawdown_tick']:.2f} tick")
        logger.info("=" * 50)
        logger.info("Trading system stopped")


# DI: 実装選択（algo4固有実装を注入）
def create_trading_system():
    # パラメータ取得
    strategy_params = config.STRATEGY_PARAMS
    level_config = config.LEVEL_CONFIG
    symbols = config.TARGET_SYMBOLS or []
    excel_data = None
    if not config.DRY_RUN:
        try:
            excel_data = win32com.client.Dispatch("Excel.Application")
            excel_data.Visible = True
            logger.info("Excel COM connection established (Data Collection)")
        except Exception as e:
            logger.error(f"Failed to connect to Excel for data collection: {e}")
            raise
    # 実装注入
    strategy = CounterTradeStrategy(strategy_params)
    level_generator = LevelGenerator(level_config)
    data_collector = LiveDataCollector(symbols, excel_data=excel_data)
    order_executor = OrderExecutor(dry_run=config.DRY_RUN)
    return TradingSystem(strategy, level_generator, data_collector, order_executor)


def main():
    """エントリーポイント"""
    print("=" * 60)
    print("実トレードシステム (algo4_counter_trade)")
    print("=" * 60)
    print(f"DRY_RUN: {config.DRY_RUN}")
    
    # 設定値バリデーション
    try:
        config.validate_config()
        logger.info("Configuration validation passed")
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        print(f"\n❌ 設定エラー:\n{e}\n")
        return
    
    if not config.DRY_RUN:
        print("\n⚠️  WARNING: 本番モードで起動します ⚠️")
        response = input("本当に実行しますか？ (yes/no): ")
        if response.lower() != "yes":
            print("キャンセルしました")
            return
    
    print("\nシステムを起動します...")
    print("停止: Ctrl+C\n")
    
    system = create_trading_system()
    system.run()


if __name__ == "__main__":
    main()
