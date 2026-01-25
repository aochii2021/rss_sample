#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
実トレード設定
"""
from pathlib import Path

# ========================================
# パス設定
# ========================================
PROJECT_ROOT = Path(__file__).parent.parent.parent
TRADE_DIR = Path(__file__).parent
LOG_DIR = TRADE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# algo4_counter_tradeへのパス
ALGO_DIR = PROJECT_ROOT / "src" / "algo4_counter_trade"

# ========================================
# 戦略パラメータ（algo4_counter_trade）
# ========================================
STRATEGY_PARAMS = {
    # エントリー判定
    "k_tick": 5.0,              # レベルからの許容距離（tick）
    "strength_threshold": 0.5,  # レベル強度の最低閾値
    
    # 決済判定
    "x_tick": 10.0,             # 利確（tick）
    "y_tick": 5.0,              # 損切り（tick）
    "max_hold_bars": 60,        # 最大保有時間（1分足の本数）
    
    # LOB特徴量
    "roll_n": 20,               # OFIのローリングウィンドウ
    "k_depth": 5,               # 板の深さ（レベル数）
    
    # サポート/レジスタンス検出
    "lookback_bars": 180,       # 過去参照期間（分）
    "bin_size": 1.0,            # VPOC/HVNのビンサイズ
    "pivot_left": 3,            # スイングポイント左側
    "pivot_right": 3,           # スイングポイント右側
}

# ========================================
# リスク管理
# ========================================
RISK_PARAMS = {
    # ポジション管理
    "max_positions": 3,          # 同時保有最大数
    "max_position_per_symbol": 1, # 1銘柄あたりの最大ポジション数
    
    # 資金管理
    "max_daily_loss_tick": 100,  # 1日の最大損失（tick）
    "position_size": 100,         # 1ポジションのサイズ（株数）
    
    # 取引時間
    "trading_sessions": {
        "morning": ("09:00", "11:25"),   # 前場（終了5分前まで）
        "afternoon": ("12:30", "15:10"),  # 後場（終了5分前まで）
    },
    
    # 緊急停止条件
    "emergency_stop": {
        "consecutive_losses": 5,     # 連続損失回数
        "drawdown_tick": 50,         # 最大ドローダウン（tick）
    }
}

# ========================================
# MarketSpeed II RSS設定
# ========================================
RSS_PARAMS = {
    # データ更新間隔
    "update_interval_sec": 1.0,  # 板情報更新間隔（秒）
    
    # データパス
    "watchlist_path": PROJECT_ROOT / "src/get_rss_market_order_book/input/watchlist.csv",
    
    # RSS接続タイムアウト
    "connection_timeout_sec": 30,
    
    # 約定確認タイムアウト
    "order_filled_check_timeout_sec": 1,  # 1回の約定確認タイムアウト（秒）
    "pending_order_timeout_sec": 30,      # pending注文の最大待機時間（秒）
}

# ========================================
# 信用取引設定
# ========================================
MARGIN_PARAMS = {
    # 信用区分
    # 1: 制度信用（6ヶ月）
    # 2: 一般信用（無制限）
    # 3: 一般信用（14日）
    # 4: 一般信用（いちにち）
    "margin_type": "4",  # デフォルト: いちにち信用（手数料安い）
    
    # 口座区分
    # 0: 特定口座
    # 1: 一般口座
    "account_type": "0",  # デフォルト: 特定口座
}

# ========================================
# ロギング設定
# ========================================
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    
    # ファイル出力
    "trade_log": LOG_DIR / "trade_{date}.log",
    "position_log": LOG_DIR / "position_{date}.csv",
    "order_log": LOG_DIR / "order_{date}.csv",
}

# ========================================
# 動作モード
# ========================================
# DRY_RUN = True: シミュレーションモード（注文実行しない）
# DRY_RUN = False: 本番モード（実際に注文実行）
DRY_RUN = True  # 初期値は安全のためTrue

# ========================================
# 対象銘柄
# ========================================
# None: watchlist全体
# リスト: 指定銘柄のみ（例: ["3350", "9501"]）
TARGET_SYMBOLS = None

# ========================================
# レベル設定
# ========================================
LEVEL_CONFIG = {
    "level_types": {
        "pivot_sr": {"enable": True, "left": 3, "right": 3},
        "consolidation": {"enable": True, "window": 20},
        "psychological": {"enable": True},
        "ma5": {"enable": True},
        "ma25": {"enable": True},
    },
    "common": {
        "strength_threshold": 0.5,
        "min_distance": 3.0,
    }
}

# ========================================
# 設定値バリデーション
# ========================================
def validate_config():
    """
    設定値の妥当性をチェック
    
    Raises:
        ValueError: 設定値が不正な場合
    """
    errors = []
    
    # STRATEGY_PARAMS検証
    if STRATEGY_PARAMS["k_tick"] <= 0:
        errors.append("k_tick must be positive")
    if STRATEGY_PARAMS["strength_threshold"] < 0 or STRATEGY_PARAMS["strength_threshold"] > 1:
        errors.append("strength_threshold must be between 0 and 1")
    if STRATEGY_PARAMS["x_tick"] <= 0:
        errors.append("x_tick must be positive")
    if STRATEGY_PARAMS["y_tick"] <= 0:
        errors.append("y_tick must be positive")
    if STRATEGY_PARAMS["max_hold_bars"] <= 0:
        errors.append("max_hold_bars must be positive")
    if STRATEGY_PARAMS["roll_n"] <= 0:
        errors.append("roll_n must be positive")
    if STRATEGY_PARAMS["k_depth"] not in [1, 2, 3, 4, 5]:
        errors.append("k_depth must be between 1 and 5")
    if STRATEGY_PARAMS["lookback_bars"] <= 0:
        errors.append("lookback_bars must be positive")
    
    # RISK_PARAMS検証
    if RISK_PARAMS["max_positions"] <= 0:
        errors.append("max_positions must be positive")
    if RISK_PARAMS["max_position_per_symbol"] <= 0:
        errors.append("max_position_per_symbol must be positive")
    if RISK_PARAMS["max_daily_loss_tick"] <= 0:
        errors.append("max_daily_loss_tick must be positive")
    if RISK_PARAMS["position_size"] <= 0:
        errors.append("position_size must be positive")
    if RISK_PARAMS["position_size"] % 100 != 0:
        errors.append("position_size must be multiple of 100 (unit share)")
    
    # RSS_PARAMS検証
    if RSS_PARAMS["update_interval_sec"] <= 0:
        errors.append("update_interval_sec must be positive")
    if RSS_PARAMS["connection_timeout_sec"] <= 0:
        errors.append("connection_timeout_sec must be positive")
    if RSS_PARAMS["order_filled_check_timeout_sec"] <= 0:
        errors.append("order_filled_check_timeout_sec must be positive")
    if RSS_PARAMS["pending_order_timeout_sec"] <= 0:
        errors.append("pending_order_timeout_sec must be positive")
    if not RSS_PARAMS["watchlist_path"].exists():
        errors.append(f"watchlist_path does not exist: {RSS_PARAMS['watchlist_path']}")
    
    # MARGIN_PARAMS検証
    if MARGIN_PARAMS["margin_type"] not in ["1", "2", "3", "4"]:
        errors.append("margin_type must be one of: 1, 2, 3, 4")
    if MARGIN_PARAMS["account_type"] not in ["0", "1"]:
        errors.append("account_type must be one of: 0, 1")
    
    # DRY_RUN検証
    if not isinstance(DRY_RUN, bool):
        errors.append("DRY_RUN must be boolean")
    
    if errors:
        error_msg = "Configuration validation failed:\n  - " + "\n  - ".join(errors)
        raise ValueError(error_msg)
    
    return True
