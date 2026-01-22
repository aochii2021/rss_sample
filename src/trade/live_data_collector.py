#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
リアルタイムデータ収集
MarketSpeed II RSSから板情報を取得し、LOB特徴量を計算
"""
import sys
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# algo4_counter_tradeのモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent / "algo4_counter_trade"))
from lob_features import compute_features_ms2

import config

logger = logging.getLogger(__name__)


class LiveDataCollector:
    """リアルタイムデータ収集クラス"""
    
    def __init__(self, symbols: list):
        """
        Args:
            symbols: 監視対象銘柄コードのリスト
        """
        self.symbols = symbols
        self.roll_n = config.STRATEGY_PARAMS["roll_n"]
        self.k_depth = config.STRATEGY_PARAMS["k_depth"]
        
        # データバッファ（銘柄ごと）
        self.lob_buffer = {sym: [] for sym in symbols}
        self.ohlc_buffer = {sym: [] for sym in symbols}
        
        logger.info(f"LiveDataCollector initialized: {len(symbols)} symbols")
    
    def fetch_board_data(self) -> pd.DataFrame:
        """
        MarketSpeed II RSSから板情報を取得
        
        Returns:
            板情報DataFrame（複数銘柄）
        """
        try:
            # TODO: 実際のRSS取得処理を実装
            # 現在はダミーデータを返す
            logger.warning("fetch_board_data: Using dummy data (RSS not implemented)")
            
            # ダミーデータ（実装例）
            dummy_data = []
            for sym in self.symbols:
                dummy_data.append({
                    "記録日時": datetime.now(),
                    "銘柄コード": sym,
                    "現在値": 1000.0,
                    "最良売気配値1": 1001.0,
                    "最良売気配数量1": 100,
                    "最良買気配値1": 999.0,
                    "最良買気配数量1": 100,
                })
            
            return pd.DataFrame(dummy_data)
            
        except Exception as e:
            logger.error(f"Failed to fetch board data: {e}")
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
