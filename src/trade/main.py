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

import config
print("=== config.py path ===", config.__file__)
print("=== DRY_RUN value ===", config.DRY_RUN)

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
    def _setup_excel_sheet(self):
        """Sheet1をクリアし、板情報数式を設定する（初回のみ）"""
        ws = self.excel_book.Worksheets('Sheet1')
        ws.UsedRange.ClearContents()
        # 板情報数式設定（get_rss_market_order_book/main.pyのロジックを移植）
        from common.rss import MarketStatusItem, RssMarket
        # 監視銘柄リスト
        stock_code_list = self.symbols
        # 項目リスト
        item_list = [item for item in MarketStatusItem]
        # RssMarketでExcel数式を設定（get_rss_market_order_bookと同じ）
        self.rss_market = RssMarket(ws, stock_code_list, item_list)
        self.excel_ws = ws
        # 初回データ取得（数式設定確認）
        self._record_market_data(first=True)

    def _record_market_data(self, first=False):
        """板情報をExcelから取得し、csvに追記"""
        import pandas as pd
        from datetime import datetime
        now = datetime.now()
        # DataFrame取得（get_rss_market_order_bookのget_all_rss_market相当）
        df = self.rss_market.get_dataframe()
        df.insert(0, '記録日時', now.strftime('%Y-%m-%d %H:%M:%S'))
        output_file = self.session_csv_path
        if first or not Path(output_file).exists():
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
        else:
            df.to_csv(output_file, mode='a', header=False, index=False, encoding='utf-8-sig')
        print(f"[{now.strftime('%H:%M:%S')}] 板情報をCSVに保存しました: {output_file}")

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
        # strategy_paramsを保持
        if hasattr(strategy, 'params'):
            self.strategy_params = strategy.params
        elif hasattr(strategy, 'strategy_params'):
            self.strategy_params = strategy.strategy_params
        else:
            # create_trading_system()から渡す場合は引数追加が必要
            self.strategy_params = {}
        # Excelインスタンス生成・一意名でワークブック保存
        import win32com.client
        now = datetime.now()
        try:
            try:
                # 既存Excelに接続
                self.excel_data = win32com.client.GetObject(Class="Excel.Application")
                logger.info("Excel instance found (GetObject)")
            except Exception:
                # 未起動なら新規起動
                self.excel_data = win32com.client.Dispatch("Excel.Application")
                self.excel_data.Visible = True
                logger.info("Excel instance started (Dispatch)")
            self.excel_book_name = f"TradeBoard_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"
            self.excel_book = self.excel_data.Workbooks.Add()
            self.excel_book.SaveAs(str(config.LOG_DIR / self.excel_book_name))
            logger.info(f"Excel COM connection established (Data Collection), book: {self.excel_book_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Excel: {e}")
            raise
        # セッションディレクトリ・csvパス生成
        self.session_dir = Path(config.LOG_DIR) / f"session_{now.strftime('%Y%m%d_%H%M')}"
        self.session_dir.mkdir(exist_ok=True)
        self.session_csv_path = str(self.session_dir / "rss_market_data.csv")
        # Excelシート初期化・数式設定
        self._setup_excel_sheet()

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
        
        lookback_bars = self.strategy_params.get("lookback_bars", 60)
        for symbol in self.symbols:
            ohlc_history = self.data_collector.get_history(
                symbol,
                lookback_bars=lookback_bars
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
        test_order_sent = False
        start_time = datetime.now()

        try:
            import time
            interval_sec = 60  # 1分ごとに固定
            last_record_minute = None

            while self.is_running:
                now_dt = datetime.now()
                now_minute = now_dt.replace(second=0, microsecond=0)
                # 毎分00秒に記録
                if last_record_minute is None or now_minute > last_record_minute:
                    try:
                        logger.info("[板情報記録トリガー] 1分ごとに板情報を記録します")
                        self._record_market_data()
                    except Exception as e:
                        logger.error(f"板情報記録エラー: {e}", exc_info=True)
                    last_record_minute = now_minute

                # 5分経過後に1度だけテスト注文
                if not test_order_sent and (now_dt - start_time).total_seconds() >= 120:
                    logger.info("[TEST] 5分経過したのでテスト注文を発行します (3350, 450円)")
                    test_signal = {
                        "symbol": "3350",
                        "action": "buy",
                        "price": 450,
                        "level": 450,
                        "level_kind": "manual_test",
                        "level_strength": 1.0,
                        "reason": "manual test trigger after 5min"
                    }
                    self.order_executor.open_position(test_signal)
                    test_order_sent = True

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
                time.sleep(1)

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
    # 実装注入
    strategy = CounterTradeStrategy(strategy_params)
    level_generator = LevelGenerator(level_config)
    data_collector = LiveDataCollector(symbols)
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
    
    # セッションごとにディレクトリを作成し、その中に注文用Excelを保存
    from datetime import datetime
    import os
    session_time = datetime.now().strftime('%Y%m%d_%H%M')
    session_dir = os.path.join(str(config.LOG_DIR), f"session_{session_time}")
    os.makedirs(session_dir, exist_ok=True)
    session_excel_name = f"order_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    session_excel_path = os.path.join(session_dir, session_excel_name)
    config.ORDER_EXCEL_PATH = session_excel_path
    # 空のExcelファイルを新規作成（存在しない場合）
    if not os.path.exists(session_excel_path):
        import win32com.client
        excel = None
        try:
            excel = win32com.client.GetObject(Class="Excel.Application")
        except Exception:
            try:
                excel = win32com.client.Dispatch("Excel.Application")
            except Exception as e:
                print(f"Excel起動失敗: {e}")
                raise
        if not hasattr(excel, "Workbooks"):
            print("Excelインスタンス取得失敗: Workbooks属性がありません")
            raise RuntimeError("Excel COMオブジェクトのWorkbooks属性取得に失敗しました")
        wb = excel.Workbooks.Add()
        wb.SaveAs(session_excel_path)
        wb.Close()
        excel.Quit()
    print(f"[INFO] 注文用Excelファイル: {session_excel_path}")

    system = create_trading_system()

    # --- テスト用: ダミー注文を1件だけ強制発行（本番ロジックに影響なし） ---
    print("[TEST] ダミー注文を1件だけ発行します（本番ロジックには影響しません）")
    test_signal = {
        "symbol": "6758",  # ソニー等、任意の上場銘柄コード
        "action": "buy",
        "price": 500,
        "level": 500,
        "level_kind": "test",
        "level_strength": 1.0,
        "reason": "manual test trigger"
    }
    system.order_executor.open_position(test_signal)
    print("[TEST] ダミー注文発行完了。以降は本来のシステム処理に移行します。\n")

    system.run()


if __name__ == "__main__":
    main()
