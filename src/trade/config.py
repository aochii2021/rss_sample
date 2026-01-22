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
