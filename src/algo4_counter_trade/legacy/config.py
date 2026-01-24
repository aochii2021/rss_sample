#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
algo4_counter_trade2 設定ファイル

バックテストパラメータ、銘柄別設定、除外銘柄リストを管理
"""

# =============================================================================
# デフォルトパラメータ
# =============================================================================

DEFAULT_PARAMS = {
    # レベル反応帯の幅（tick単位）
    # レベルから±k_tick以内に価格が入ったらエントリー条件をチェック
    "k_tick": 5.0,
    
    # 利確幅（tick単位）
    # エントリー価格から+x_tick動いたら利確
    "x_tick": 10.0,
    
    # 損切幅（tick単位）
    # エントリー価格から-y_tick動いたら損切
    "y_tick": 5.0,
    
    # 最大保有時間（バー数）
    # この期間保有してもTP/SLに達しない場合は強制決済
    "max_hold_bars": 60,
    
    # レベル強度の閾値（0.0-1.0）
    # この値以上の強度を持つレベルのみ使用
    "strength_th": 0.5,
    
    # OFI/depth_imb計算用のローリング期間
    "roll_n": 20,
    
    # depth_imb計算用の板の深さ
    "k_depth": 5
}

# =============================================================================
# 銘柄別パラメータ（営業時間フィルタ適用後の最適化結果: 9:00-15:00）
# =============================================================================

SYMBOL_PARAMS = {
    "3350.0": {
        "k_tick": 5.0,
        "x_tick": 5.0,
        "y_tick": 5.0,
        "max_hold_bars": 90,
        "roll_n": 20,
        "k_depth": 5
    },
    "9501.0": {
        "k_tick": 3.0,
        "x_tick": 5.0,
        "y_tick": 3.0,
        "max_hold_bars": 120,
        "roll_n": 20,
        "k_depth": 5
    },
    "9509.0": {
        "k_tick": 7.0,
        "x_tick": 5.0,
        "y_tick": 7.0,
        "max_hold_bars": 120,
        "roll_n": 20,
        "k_depth": 5
    },
    "215A": {
        "k_tick": 3.0,
        "x_tick": 5.0,
        "y_tick": 7.0,
        "max_hold_bars": 120,
        "roll_n": 20,
        "k_depth": 5
    },
    "6526.0": {
        "k_tick": 5.0,
        "x_tick": 5.0,
        "y_tick": 5.0,
        "max_hold_bars": 120,
        "roll_n": 20,
        "k_depth": 5
    },
    "5016.0": {
        "k_tick": 3.0,
        "x_tick": 10.0,
        "y_tick": 3.0,
        "max_hold_bars": 60,
        "roll_n": 20,
        "k_depth": 5
    },
}

# =============================================================================
# 除外銘柄リスト
# =============================================================================

# バックテストから除外する銘柄
# 理由: 勝率が極端に低い、データ品質に問題がある、等
EXCLUDED_SYMBOLS = [
    "6315.0",  # TOWA: 勝率4.5%、総PnL=-90.5 tick → 戦略不適合
]

# =============================================================================
# データ検証設定
# =============================================================================

# 価格異常値検出の閾値（前日比変動率）
PRICE_ANOMALY_THRESHOLD = 0.5  # ±50%以上の変動を異常とみなす

# 必須カラム定義
REQUIRED_COLUMNS = {
    "rss": ["記録日時", "銘柄コード", "最良売気配値1", "最良買気配値1"],
    "ohlc": ["timestamp", "open", "high", "low", "close", "volume", "symbol"],
    "lob_features": ["ts", "symbol", "spread", "mid", "microprice"],
    "levels": ["symbol", "kind", "level_now", "strength"],
}

# =============================================================================
# ヘルパー関数
# =============================================================================

def get_params(symbol: str) -> dict:
    """
    銘柄のパラメータを取得
    
    Args:
        symbol: 銘柄コード
    
    Returns:
        パラメータ辞書（SYMBOL_PARAMSに設定があればそれを、なければDEFAULT_PARAMSを返す）
    """
    return SYMBOL_PARAMS.get(symbol, DEFAULT_PARAMS.copy())

def is_excluded(symbol: str) -> bool:
    """
    銘柄が除外リストに含まれるか判定
    
    Args:
        symbol: 銘柄コード
    
    Returns:
        除外対象ならTrue
    """
    return symbol in EXCLUDED_SYMBOLS

def list_active_symbols(all_symbols: list) -> list:
    """
    除外銘柄を除いたアクティブ銘柄リストを返す
    
    Args:
        all_symbols: 全銘柄リスト
    
    Returns:
        除外銘柄を除いたリスト
    """
    return [s for s in all_symbols if not is_excluded(s)]
