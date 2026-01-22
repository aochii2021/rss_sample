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

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from live_data_collector import LiveDataCollector
from signal_generator import SignalGenerator
from order_executor import OrderExecutor

# ロギング設定
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


class TradingSystem:
    """実トレードシステム"""
    
    def __init__(self):
        # 監視対象銘柄の読み込み
        self.symbols = self._load_symbols()
        logger.info(f"Target symbols: {len(self.symbols)}")
        
        # コンポーネント初期化
        self.order_executor = OrderExecutor(dry_run=config.DRY_RUN)
        
        # データ取得用Excel（注文用とは別インスタンス）
        self.excel_data = None
        if not config.DRY_RUN:
            try:
                self.excel_data = win32com.client.Dispatch("Excel.Application")
                self.excel_data.Visible = True
                logger.info("Excel COM connection established (Data Collection)")
            except Exception as e:
                logger.error(f"Failed to connect to Excel for data collection: {e}")
                raise
        
        self.data_collector = LiveDataCollector(self.symbols, excel_data=self.excel_data)
        self.signal_generator = SignalGenerator()
        
        # 状態管理
        self.is_running = False
        self.current_session = None
        self.last_position_sync = datetime.now()
        
        logger.info("TradingSystem initialized")
    
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
        # リアルタイムデータ取得
        lob_data = self.data_collector.update()
        
        # 各銘柄のレベルを更新
        for symbol in self.symbols:
            # OHLC履歴を取得（サポート/レジスタンス検出用）
            ohlc_history = self.data_collector.get_history(
                symbol, 
                lookback_bars=config.STRATEGY_PARAMS["lookback_bars"]
            )
            
            if not ohlc_history.empty:
                # TODO: OHLCデータが必要（現在はLOB特徴量のみ）
                # 暫定: midをcloseとして使用
                ohlc_df = pd.DataFrame({
                    "timestamp": ohlc_history["ts"],
                    "open": ohlc_history["mid"],
                    "high": ohlc_history["mid"],
                    "low": ohlc_history["mid"],
                    "close": ohlc_history["mid"],
                    "volume": 0
                })
                
                self.signal_generator.update_levels(symbol, ohlc_df)
    
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
            
            # エントリーシグナルチェック
            signal = self.signal_generator.check_entry_signal(
                symbol, 
                current_price,
                lob_features
            )
            
            if signal:
                logger.info(f"Entry signal: {signal}")
                self.order_executor.open_position(signal)
        
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


def main():
    """エントリーポイント"""
    print("=" * 60)
    print("実トレードシステム (algo4_counter_trade)")
    print("=" * 60)
    print(f"DRY_RUN: {config.DRY_RUN}")
    
    if not config.DRY_RUN:
        print("\n⚠️  WARNING: 本番モードで起動します ⚠️")
        response = input("本当に実行しますか？ (yes/no): ")
        if response.lower() != "yes":
            print("キャンセルしました")
            return
    
    print("\nシステムを起動します...")
    print("停止: Ctrl+C\n")
    
    system = TradingSystem()
    system.run()


if __name__ == "__main__":
    main()
