"""
LOB（Limit Order Book）特徴量プロセッサ
板情報から取引に有用な特徴量を計算
"""
import sys
from pathlib import Path
from typing import Dict, Optional
import numpy as np
import pandas as pd
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class LOBProcessor:
    """
    LOB特徴量計算クラス
    
    計算する特徴量:
    - spread: スプレッド（最良売気配 - 最良買気配）
    - mid: ミッド価格（最良気配の中値）
    - qi_l1: レベル1の数量インバランス
    - microprice: マイクロ価格
    - micro_bias: マイクロ価格とミッド価格の差
    - ofi_N: Order Flow Imbalance（N期間ローリング）
    - depth_imb_k: 深度インバランス（上位k段）
    """
    
    def __init__(
        self,
        roll_n: int = 20,
        k_depth: int = 5
    ):
        """
        初期化
        
        Args:
            roll_n: OFI計算用のローリング期間
            k_depth: 深度インバランス計算用の板の深さ
        """
        self.roll_n = roll_n
        self.k_depth = k_depth
    
    def process(
        self,
        market_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        板情報から特徴量を計算
        
        Args:
            market_data: {銘柄コード: DataFrame} の辞書
            
        Returns:
            {銘柄コード: 特徴量DataFrame} の辞書
        """
        logger.info(f"LOB特徴量計算開始: {len(market_data)}銘柄")
        
        features = {}
        for symbol, df in market_data.items():
            # symbolを常に4桁str化
            norm_symbol = str(symbol)
            if norm_symbol.endswith('.0'):
                norm_symbol = norm_symbol[:-2]
            norm_symbol = norm_symbol.zfill(4)
            try:
                feat_df = self._compute_features_for_symbol(df, norm_symbol)
                features[norm_symbol] = feat_df
                logger.info(f"  {norm_symbol}: {len(feat_df)}行の特徴量生成")
            except Exception as e:
                logger.error(f"  {norm_symbol}: 特徴量計算エラー - {e}")
                continue
        
        logger.info(f"LOB特徴量計算完了: {len(features)}銘柄")
        return features
    
    def _compute_features_for_symbol(
        self,
        df: pd.DataFrame,
        symbol: str
    ) -> pd.DataFrame:
        """
        1銘柄の特徴量を計算
        
        Args:
            df: 板情報DataFrame
            symbol: 銘柄コード
            
        Returns:
            特徴量DataFrame
        """
        # タイムスタンプカラムを確認
        ts_col = self._find_timestamp_column(df)
        if ts_col is None:
            raise ValueError(f"タイムスタンプカラムが見つかりません: {symbol}")
        
        # 板気配カラムを確認
        ask_px_col = self._find_column(df, ['最良売気配値1', '最良売気配値'])
        bid_px_col = self._find_column(df, ['最良買気配値1', '最良買気配値'])
        ask_qty_col = self._find_column(df, ['最良売気配数量1', '最良売気配数量'])
        bid_qty_col = self._find_column(df, ['最良買気配数量1', '最良買気配数量'])
        
        if not all([ask_px_col, bid_px_col, ask_qty_col, bid_qty_col]):
            raise ValueError(f"必要な板情報カラムが不足: {symbol}")
        
        # 空文字・NaNを除外
        mask = (
            df[ask_px_col].notna() & df[bid_px_col].notna() &
            (df[ask_px_col] != "") & (df[bid_px_col] != "")
        )
        df = df[mask].reset_index(drop=True)
        
        if len(df) == 0:
            # 空のDataFrameを返す
            return pd.DataFrame(columns=[
                'ts', 'symbol', 'spread', 'mid', 'qi_l1',
                'microprice', 'micro_bias', f'ofi_{self.roll_n}', f'depth_imb_{self.k_depth}'
            ])
        
        # 基本データ抽出
        ask_px = df[ask_px_col].astype(float)
        bid_px = df[bid_px_col].astype(float)
        ask_qty = df[ask_qty_col].astype(float)
        bid_qty = df[bid_qty_col].astype(float)
        
        # 特徴量DataFrame作成
        out = pd.DataFrame()
        out['ts'] = df[ts_col]
        # symbolを常に4桁str化
        norm_symbol = str(symbol)
        if norm_symbol.endswith('.0'):
            norm_symbol = norm_symbol[:-2]
        norm_symbol = norm_symbol.zfill(4)
        out['symbol'] = norm_symbol
        
        # 基本特徴量
        out['spread'] = ask_px - bid_px
        out['mid'] = (ask_px + bid_px) / 2.0
        out['qi_l1'] = (bid_qty - ask_qty) / (bid_qty + ask_qty).replace(0, np.nan)
        
        # マイクロ価格
        denom = (bid_qty + ask_qty).replace(0, np.nan)
        micro = (ask_px * bid_qty + bid_px * ask_qty) / denom
        out['microprice'] = micro
        out['micro_bias'] = micro - out['mid']
        
        # Order Flow Imbalance (OFI)
        d_bid_px = bid_px.diff().fillna(0)
        d_ask_px = ask_px.diff().fillna(0)
        d_bid_sz = bid_qty.diff().fillna(0)
        d_ask_sz = ask_qty.diff().fillna(0)
        
        ofi = (
            ((d_bid_px > 0) * bid_qty + (d_bid_px == 0) * d_bid_sz) -
            ((d_ask_px < 0) * ask_qty + (d_ask_px == 0) * d_ask_sz)
        )
        out[f'ofi_{self.roll_n}'] = self._rolling_sum_numpy(ofi.values.astype(float), self.roll_n)
        
        # 深度インバランス
        bid_depth = self._compute_depth_sum(df, 'bid', self.k_depth)
        ask_depth = self._compute_depth_sum(df, 'ask', self.k_depth)
        out[f'depth_imb_{self.k_depth}'] = bid_depth - ask_depth
        
        return out
    
    def _compute_depth_sum(
        self,
        df: pd.DataFrame,
        side: str,
        k_depth: int
    ) -> pd.Series:
        """
        上位k段の数量合計を計算
        
        Args:
            df: DataFrame
            side: 'bid' or 'ask'
            k_depth: 深さ
            
        Returns:
            数量合計Series
        """
        s = None
        for i in range(1, k_depth + 1):
            col = self._make_column_name(i, side, 'qty')
            if col in df.columns:
                qty = df[col].replace("", np.nan).fillna(0).astype(float)
                s = qty if s is None else s.add(qty, fill_value=0)
        
        return s if s is not None else pd.Series([np.nan] * len(df))
    
    @staticmethod
    def _make_column_name(level: int, side: str, kind: str) -> str:
        """
        板情報カラム名を生成
        
        Args:
            level: レベル（1-10）
            side: 'ask' or 'bid'
            kind: 'px' or 'qty'
            
        Returns:
            カラム名
        """
        if side == 'ask' and kind == 'px':
            return f'最良売気配値{level}'
        if side == 'ask' and kind == 'qty':
            return f'最良売気配数量{level}'
        if side == 'bid' and kind == 'px':
            return f'最良買気配値{level}'
        if side == 'bid' and kind == 'qty':
            return f'最良買気配数量{level}'
        raise ValueError(f"Invalid side/kind: {side}/{kind}")
    
    @staticmethod
    def _rolling_sum_numpy(x: np.ndarray, n: int) -> np.ndarray:
        """
        NumPyを使った高速ローリング合計
        
        Args:
            x: 入力配列
            n: ウィンドウサイズ
            
        Returns:
            ローリング合計配列
        """
        if n <= 1:
            return x.astype(float)
        
        c = np.cumsum(np.nan_to_num(x, nan=0.0))
        out = c.copy()
        out[n:] = c[n:] - c[:-n]
        return out
    
    @staticmethod
    def _find_timestamp_column(df: pd.DataFrame) -> Optional[str]:
        """
        タイムスタンプカラムを探す
        
        Args:
            df: DataFrame
            
        Returns:
            カラム名（見つからない場合はNone）
        """
        candidates = ['timestamp', 'ts', '記録日時', '現在値詳細時刻', '現在値時刻']
        for col in candidates:
            if col in df.columns:
                return col
        return None
    
    @staticmethod
    def _find_column(df: pd.DataFrame, candidates: list) -> Optional[str]:
        """
        カラム名候補から存在するカラムを探す
        
        Args:
            df: DataFrame
            candidates: カラム名候補リスト
            
        Returns:
            カラム名（見つからない場合はNone）
        """
        for col in candidates:
            if col in df.columns:
                return col
        return None


if __name__ == "__main__":
    # テスト実行
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.data_loader import DataLoader
    from datetime import datetime
    
    logging.basicConfig(level=logging.INFO)
    
    # データ読み込み
    loader = DataLoader(
        chart_data_dir="input/chart_data",
        market_data_dir="input/market_order_book"
    )
    target_date = datetime(2026, 1, 20)
    market_data = loader.load_market_data_for_date(target_date)
    
    # LOB特徴量計算
    processor = LOBProcessor(roll_n=20, k_depth=5)
    features = processor.process(market_data)
    
    print(f"\n=== LOB特徴量計算結果 ===")
    for symbol, df in list(features.items())[:3]:
        print(f"\n{symbol}:")
        print(df.head())
        print(f"カラム: {list(df.columns)}")
