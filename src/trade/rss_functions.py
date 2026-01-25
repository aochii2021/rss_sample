#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MarketSpeed II RSS関数ラッパー
Excel COM経由でRSS関数を呼び出し
"""
import logging
import time
from functools import wraps
from typing import Optional, Dict, Any, List, Callable
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


def retry_on_error(max_retries: int = 3, delay_seconds: float = 1.0):
    """
    エラー時にリトライするデコレータ
    
    Args:
        max_retries: 最大リトライ回数（初回実行 + リトライ回数）
        delay_seconds: リトライ間隔（秒）
    
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {delay_seconds}s..."
                        )
                        time.sleep(delay_seconds)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )
            
            # 全てのリトライが失敗した場合
            raise last_exception
        
        return wrapper
    return decorator


class RSSFunctions:
    def get_all_order_ids(self) -> list:
        """
        全注文の発注IDリスト（int）を返す。該当列がなければ空リスト。
        デバッグ用にDataFrame内容・IDリストをログ出力
        """
        try:
            df = self.get_order_list()
            logger.debug(f"[get_all_order_ids] order_list DataFrame: columns={list(df.columns)}, shape={df.shape}")
            if not df.empty and '発注ID' in df.columns:
                id_list = [int(x) for x in df['発注ID'] if str(x).isdigit()]
                logger.debug(f"[get_all_order_ids] 発注IDリスト: {id_list}")
                return id_list
            else:
                logger.debug(f"[get_all_order_ids] 発注ID列なし or DataFrame空")
        except Exception as e:
            logger.warning(f"get_all_order_ids失敗: {e}")
        return []
    
    def __init__(self, excel):
        """
        Args:
            excel: win32com.client.Dispatch("Excel.Application")
        """
        self.excel = excel
        if not self.excel:
            raise ValueError("Excel instance is required")
        
        logger.info("RSSFunctions initialized")
    
    @retry_on_error(max_retries=3, delay_seconds=1.0)
    def get_market_price(self, symbol: str) -> Optional[float]:
        """
        現在価格を取得（RssMarket）
        
        Args:
            symbol: 銘柄コード
        
        Returns:
            現在価格、取得失敗時はNone
        """
        try:
            # RssMarket関数で現在値を取得
            price = self.excel.Run("RssMarket", f"{symbol}.T", "現在値")
            
            if price and isinstance(price, (int, float)):
                return float(price)
            
            logger.warning(f"Failed to get price for {symbol}: {price}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting market price for {symbol}: {e}")
            return None
    
    @retry_on_error(max_retries=3, delay_seconds=1.0)
    def get_order_list(
        self,
        order_status: str = "",  # 空=全て、"0"=受付中、"1"=発注済、"2"=訂正中等
        order_type: str = "",    # 空=全て、"0"=現物、"1"=信用
        symbol: str = "",        # 空=全銘柄
    ) -> pd.DataFrame:
        """
        注文一覧を取得（RssOrderList）
        
        Args:
            order_status: 注文状況フィルタ
            order_type: 注文種類フィルタ
            symbol: 銘柄コードフィルタ
        
        Returns:
            注文一覧DataFrame
        """
        try:
            # RssOrderList関数を呼び出し
            result = self.excel.Run(
                "RssOrderList",
                1,              # ヘッダー行あり
                order_status,   # 注文状況
                order_type,     # 注文種類
                symbol,         # 銘柄コード
                "",             # 口座区分
                "",             # 売買
                "",             # 信用取引
                "",             # 信用区分
                "",             # アルゴ注文
                ""              # アルゴ注文種類
            )
            
            if result and isinstance(result, (tuple, list)):
                # Excelの戻り値を2次元リストに変換
                data = list(result)
                if len(data) > 1:  # ヘッダー + データ行
                    headers = data[0]
                    rows = data[1:]
                    df = pd.DataFrame(rows, columns=headers)
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting order list: {e}")
            return pd.DataFrame()
    
    @retry_on_error(max_retries=3, delay_seconds=1.0)
    def get_execution_list(
        self,
        order_type: str = "",  # 空=全て、"0"=現物、"1"=信用
        symbol: str = "",      # 空=全銘柄
    ) -> pd.DataFrame:
        """
        約定一覧を取得（RssExecutionList）
        
        Args:
            order_type: 注文種類フィルタ
            symbol: 銘柄コードフィルタ
        
        Returns:
            約定一覧DataFrame
        """
        try:
            result = self.excel.Run(
                "RssExecutionList",
                1,           # ヘッダー行あり
                order_type,  # 注文種類
                symbol,      # 銘柄コード
                "",          # 口座区分
                "",          # 信用区分
                ""           # 売買
            )
            
            if result and isinstance(result, (tuple, list)):
                data = list(result)
                if len(data) > 1:
                    headers = data[0]
                    rows = data[1:]
                    df = pd.DataFrame(rows, columns=headers)
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting execution list: {e}")
            return pd.DataFrame()
    
    @retry_on_error(max_retries=3, delay_seconds=1.0)
    def get_margin_positions(
        self,
        symbol: str = "",        # 空=全銘柄
        account_type: str = "",  # 空=全て、"0"=特定、"1"=一般
        margin_type: str = "",   # 空=全て、"1"=制度、"2"=一般無制限等
    ) -> pd.DataFrame:
        """
        信用建玉一覧を取得（RssMarginPositionList）
        
        Args:
            symbol: 銘柄コードフィルタ
            account_type: 口座区分フィルタ
            margin_type: 信用区分フィルタ
        
        Returns:
            信用建玉一覧DataFrame
        """
        try:
            result = self.excel.Run(
                "RssMarginPositionList",
                1,             # ヘッダー行あり
                symbol,        # 銘柄コード
                account_type,  # 口座区分
                margin_type,   # 信用区分
                "",            # 売買
                ""             # 直近最終返済日
            )
            
            if result and isinstance(result, (tuple, list)):
                data = list(result)
                if len(data) > 1:
                    headers = data[0]
                    rows = data[1:]
                    df = pd.DataFrame(rows, columns=headers)
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting margin positions: {e}")
            return pd.DataFrame()
    
    @retry_on_error(max_retries=3, delay_seconds=1.0)
    def get_margin_power(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        信用新規建余力を取得（RssMarginPower）
        
        Args:
            symbol: 銘柄コード
        
        Returns:
            余力情報Dict、取得失敗時はNone
        """
        try:
            result = self.excel.Run(
                "RssMarginPower",
                1,              # ヘッダー行あり
                f"{symbol}.T"   # 銘柄コード
            )
            
            if result and isinstance(result, (tuple, list)):
                data = list(result)
                if len(data) > 1:
                    headers = data[0]
                    values = data[1]
                    
                    # Dict形式で返す
                    power_info = dict(zip(headers, values))
                    return power_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting margin power for {symbol}: {e}")
            return None
    
    @retry_on_error(max_retries=3, delay_seconds=1.0)
    def get_order_status(self, order_id: int) -> Optional[str]:
        """
        発注IDごとの注文状況を取得（RssOrderStatus）
        
        Args:
            order_id: 発注ID
        
        Returns:
            注文状況文字列、取得失敗時はNone
        """
        try:
            status = self.excel.Run("RssOrderStatus", order_id)
            
            if status and isinstance(status, str):
                return status
            
            logger.warning(f"Failed to get order status for ID {order_id}: {status}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting order status for ID {order_id}: {e}")
            return None
    
    def check_order_filled(self, order_id: int, timeout_sec: int = 5) -> bool:
        """
        注文が約定したかチェック（堅牢化版）
        
        Args:
            order_id: 発注ID
            timeout_sec: タイムアウト秒数
        
        Returns:
            True: 約定済み、False: 未約定orエラー
        """
        import time
        start_time = time.time()
        
        # 約定状態文字列の定義（MarketSpeed II RSSの仕様）
        FILLED_STATUSES = ["約定", "全部約定", "一部約定"]
        FAILED_STATUSES = ["取消", "失効", "エラー", "却下", "訂正取消"]
        
        while time.time() - start_time < timeout_sec:
            status = self.get_order_status(order_id)
            
            if status:
                # 完全一致チェック（部分一致によるfalse positiveを回避）
                status_stripped = status.strip()
                
                # 約定済み状態をチェック
                for filled_status in FILLED_STATUSES:
                    if filled_status in status_stripped:
                        logger.info(f"Order {order_id} filled: {status_stripped}")
                        return True
                
                # 失敗/キャンセル状態をチェック
                for failed_status in FAILED_STATUSES:
                    if failed_status in status_stripped:
                        logger.warning(f"Order {order_id} cancelled/failed: {status_stripped}")
                        return False
            
            time.sleep(0.5)
        
        logger.warning(f"Order {order_id} timeout after {timeout_sec}s")
        return False
