#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
リアルタイムデータ収集
MarketSpeed II RSSから板情報を取得し、LOB特徴量を計算
"""
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# algo4_counter_tradeのモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent / "algo4_counter_trade"))
from lob_features_legacy import compute_features_ms2

import config
from rss_functions import RSSFunctions

logger = logging.getLogger(__name__)


class LiveDataCollector:
    """リアルタイムデータ収集クラス"""
    
    def __init__(self, symbols: list, excel_data=None):
        """
        Args:
            symbols: 監視対象銘柄コードのリスト
            excel_data: データ取得専用Excelインスタンス（DRY_RUN=False時）
        """
        self.symbols = symbols
        self.excel_data = excel_data
        self.rss_data = RSSFunctions(excel_data) if excel_data else None
        self.roll_n = config.STRATEGY_PARAMS["roll_n"]
        self.k_depth = config.STRATEGY_PARAMS["k_depth"]
        
        # データバッファ（銘柄ごと）
        self.lob_buffer = {sym: [] for sym in symbols}
        self.ohlc_buffer = {sym: [] for sym in symbols}
        
        logger.info(f"LiveDataCollector initialized: {len(symbols)} symbols")
    
    def fetch_board_data(self) -> pd.DataFrame:
        """
        MarketSpeed II RSSから板情報を取得（bid/ask各5本）
        リトライ機構付き（最大3回、1秒間隔）
        
        Returns:
            板情報DataFrame（複数銘柄）
        """
        # DRY_RUNモード：ダミーデータを返す
        if not self.excel_data:
            logger.debug("DRY_RUN mode: returning dummy data")
            return pd.DataFrame()
        
        max_retries = 3
        retry_delay = 1.0
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # 各銘柄の板情報をRssMarketで取得
                board_data = []
                
                for symbol in self.symbols:
                    row_data = {
                        "ts": datetime.now(),
                        "symbol": symbol
                    }
                    
                    # RssMarketで板の気配値を取得（bid/ask各5本）
                    try:
                        # 買気配（bid）1〜5
                        for i in range(1, 6):
                            bid_px = self.excel_data.Run("RssMarket", f"{symbol}.T", f"買気配値段{i}")
                            bid_qty = self.excel_data.Run("RssMarket", f"{symbol}.T", f"買気配数量{i}")
                            row_data[f"bid_px_{i}"] = bid_px if bid_px else None
                            row_data[f"bid_qty_{i}"] = bid_qty if bid_qty else None
                        
                        # 売気配（ask）1〜5
                        for i in range(1, 6):
                            ask_px = self.excel_data.Run("RssMarket", f"{symbol}.T", f"売気配値段{i}")
                            ask_qty = self.excel_data.Run("RssMarket", f"{symbol}.T", f"売気配数量{i}")
                            row_data[f"ask_px_{i}"] = ask_px if ask_px else None
                            row_data[f"ask_qty_{i}"] = ask_qty if ask_qty else None
                        
                        board_data.append(row_data)
                    except Exception as e:
                        logger.warning(f"Failed to fetch board data for {symbol}: {e}")
                
                if board_data:
                    df = pd.DataFrame(board_data)
                    logger.debug(f"Fetched board data for {len(board_data)} symbols")
                    return df
                else:
                    logger.warning("No board data fetched")
                    return pd.DataFrame()
                
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(
                        f"fetch_board_data failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(f"fetch_board_data failed after {max_retries} attempts: {e}")
        
        # 全てのリトライが失敗した場合、空DataFrameを返す
        return pd.DataFrame()
    
    def compute_lob_features(self, board_df: pd.DataFrame) -> pd.DataFrame:
        """
        LOB特徴量を計算
        
        Args:
            board_df: 板情報DataFrame
        
        Returns:
            LOB特徴量DataFrame
        """
        try:
            if board_df.empty:
                return pd.DataFrame()
            
            # algo4_counter_tradeのLOB特徴量計算を使用
            features_df = compute_features_ms2(
                board_df, 
                roll_n=self.roll_n, 
                k_depth=self.k_depth
            )
            
            logger.debug(f"Computed LOB features: {len(features_df)} rows")
            return features_df
            
        except Exception as e:
            logger.error(f"Failed to compute LOB features: {e}")
            return pd.DataFrame()
    
    def update(self) -> dict:
        """
        データ更新（1サイクル）
        
        Returns:
            銘柄ごとのLOB特徴量辞書 {symbol: DataFrame}
        """
        # 板情報取得
        board_df = self.fetch_board_data()
        if board_df.empty:
            return {}
        
        # LOB特徴量計算
        features_df = self.compute_lob_features(board_df)
        if features_df.empty:
            return {}
        
        # 銘柄ごとに分割してバッファに追加
        result = {}
        for sym in self.symbols:
            sym_features = features_df[features_df["symbol"] == sym]
            if not sym_features.empty:
                self.lob_buffer[sym].append(sym_features)
                
                # 最新データを返す
                result[sym] = sym_features.iloc[-1]
        
        return result
    
    def get_history(self, symbol: str, lookback_bars: int = 180) -> pd.DataFrame:
        """
        指定銘柄の過去データを取得
        
        Args:
            symbol: 銘柄コード
            lookback_bars: 過去何本分取得するか
        
        Returns:
            LOB特徴量履歴DataFrame
        """
        if symbol not in self.lob_buffer:
            return pd.DataFrame()
        
        # バッファから結合
        if not self.lob_buffer[symbol]:
            return pd.DataFrame()
        
        history_df = pd.concat(self.lob_buffer[symbol], ignore_index=True)
        
        # 最新lookback_bars本を返す
        return history_df.tail(lookback_bars).reset_index(drop=True)


if __name__ == "__main__":
    # テスト用
    logging.basicConfig(
        level=logging.DEBUG,
        format=config.LOGGING_CONFIG["format"]
    )
    
    test_symbols = ["3350", "9501"]
    collector = LiveDataCollector(test_symbols)
    
    # 1回更新
    data = collector.update()
    print(f"Collected data: {len(data)} symbols")
    for sym, features in data.items():
        print(f"  {sym}: {features}")
