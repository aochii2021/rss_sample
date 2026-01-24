#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
データ検証ユーティリティ

ファイルの存在確認、カラム検証、異常値検出などを提供
"""
import os
import sys
import logging
from typing import List, Dict, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# =============================================================================
# ファイル・カラム検証
# =============================================================================

def validate_file_exists(path: str) -> bool:
    """
    ファイルの存在を確認
    
    Args:
        path: ファイルパス
    
    Returns:
        存在すればTrue
    
    Raises:
        FileNotFoundError: ファイルが存在しない場合
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    return True

def validate_csv_columns(path: str, required_columns: List[str], encoding: str = "utf-8-sig") -> bool:
    """
    CSVファイルのカラム検証
    
    Args:
        path: CSVファイルパス
        required_columns: 必須カラムのリスト
        encoding: エンコーディング
    
    Returns:
        検証成功ならTrue
    
    Raises:
        ValueError: 必須カラムが不足している場合
    """
    validate_file_exists(path)
    
    # ヘッダー行のみ読み込み
    df = pd.read_csv(path, nrows=1, encoding=encoding)
    
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")
    
    logger.info(f"CSV validation passed: {path}")
    return True

def validate_csv_not_empty(path: str, encoding: str = "utf-8-sig") -> bool:
    """
    CSVファイルが空でないことを確認
    
    Args:
        path: CSVファイルパス
        encoding: エンコーディング
    
    Returns:
        データが存在すればTrue
    
    Raises:
        ValueError: ファイルが空の場合
    """
    validate_file_exists(path)
    
    df = pd.read_csv(path, nrows=1, encoding=encoding)
    if len(df) == 0:
        raise ValueError(f"CSV file is empty: {path}")
    
    return True

# =============================================================================
# データ整合性検証
# =============================================================================

def validate_levels(levels: List[Dict[str, Any]]) -> bool:
    """
    レベルデータの整合性検証
    
    Args:
        levels: レベルデータのリスト
    
    Returns:
        検証成功ならTrue
    
    Raises:
        ValueError: 不正なデータが含まれる場合
    """
    for i, lv in enumerate(levels):
        # level_now のNaNチェック
        if "level_now" not in lv or pd.isna(lv["level_now"]):
            raise ValueError(f"Invalid level at index {i}: level_now is NaN or missing")
        
        # strength の範囲チェック
        strength = lv.get("strength", 0.5)
        if not (0.0 <= strength <= 1.0):
            raise ValueError(f"Invalid strength at index {i}: {strength} (must be in [0.0, 1.0])")
        
        # 必須フィールドチェック
        required_fields = ["kind", "level_now"]
        missing = [f for f in required_fields if f not in lv]
        if missing:
            raise ValueError(f"Missing required fields at index {i}: {missing}")
    
    logger.info(f"Level validation passed: {len(levels)} levels")
    return True

def detect_price_anomaly(df: pd.DataFrame, col: str = "close", threshold: float = 0.5) -> pd.DataFrame:
    """
    価格の異常変動を検出
    
    Args:
        df: 価格データを含むDataFrame
        col: 価格カラム名
        threshold: 異常判定の閾値（前日比変動率、デフォルト50%）
    
    Returns:
        異常値を含む行のDataFrame
    """
    if col not in df.columns:
        logger.warning(f"Column '{col}' not found in DataFrame")
        return pd.DataFrame()
    
    pct_change = df[col].pct_change().abs()
    anomalies = df[pct_change > threshold]
    
    if not anomalies.empty:
        logger.warning(f"Price anomalies detected: {len(anomalies)} rows with >{threshold*100}% change")
        for idx, row in anomalies.head(5).iterrows():
            logger.warning(f"  Row {idx}: {col}={row[col]}, change={pct_change.loc[idx]*100:.1f}%")
    
    return anomalies

def validate_timestamp_continuity(df: pd.DataFrame, ts_col: str = "timestamp", max_gap_minutes: int = 10) -> bool:
    """
    タイムスタンプの連続性を検証
    
    Args:
        df: タイムスタンプを含むDataFrame
        ts_col: タイムスタンプカラム名
        max_gap_minutes: 許容する最大ギャップ（分）
    
    Returns:
        検証成功ならTrue
    """
    if ts_col not in df.columns:
        raise ValueError(f"Timestamp column '{ts_col}' not found")
    
    df_sorted = df.sort_values(ts_col)
    df_sorted[ts_col] = pd.to_datetime(df_sorted[ts_col])
    
    gaps = df_sorted[ts_col].diff()
    large_gaps = gaps[gaps > pd.Timedelta(minutes=max_gap_minutes)]
    
    if not large_gaps.empty:
        logger.warning(f"Large timestamp gaps detected: {len(large_gaps)} gaps > {max_gap_minutes}min")
        for idx in large_gaps.head(3).index:
            logger.warning(f"  Gap at index {idx}: {gaps.loc[idx]}")
        return False
    
    logger.info(f"Timestamp continuity validated: max_gap={gaps.max()}")
    return True

# =============================================================================
# ディレクトリ操作
# =============================================================================

def ensure_directory(path: str) -> None:
    """
    ディレクトリが存在しない場合は作成
    
    Args:
        path: ディレクトリパス
    """
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        logger.info(f"Created directory: {path}")

def ensure_output_directory(file_path: str) -> None:
    """
    出力ファイルのディレクトリを確保
    
    Args:
        file_path: 出力ファイルのパス
    """
    dir_path = os.path.dirname(file_path)
    if dir_path:
        ensure_directory(dir_path)
