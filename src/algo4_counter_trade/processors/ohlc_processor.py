"""
OHLCプロセッサ
板情報から分足OHLCを生成
"""
import sys
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class OHLCProcessor:
    """
    OHLC（Open, High, Low, Close）データ生成クラス
    
    板情報のミッド価格から分足OHLCを生成します。
    """
    
    def __init__(self, freq: str = '1min'):
        """
        初期化
        
        Args:
            freq: リサンプリング周波数（'1min', '5min', '1h', '1D'など）
        """
        self.freq = freq
    
    def process(
        self,
        market_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        板情報からOHLCを生成
        
        Args:
            market_data: {銘柄コード: DataFrame} の辞書
            
        Returns:
            {銘柄コード: OHLCDataFrame} の辞書
        """
        logger.info(f"OHLC生成開始: {len(market_data)}銘柄, 周波数={self.freq}")
        
        ohlc_data = {}
        for symbol, df in market_data.items():
            try:
                ohlc_df = self._create_ohlc_for_symbol(df, symbol)
                ohlc_data[symbol] = ohlc_df
                logger.info(f"  {symbol}: {len(ohlc_df)}本のローソク足生成")
            except Exception as e:
                logger.error(f"  {symbol}: OHLC生成エラー - {e}")
                continue
        
        logger.info(f"OHLC生成完了: {len(ohlc_data)}銘柄")
        return ohlc_data
    
    def _create_ohlc_for_symbol(
        self,
        df: pd.DataFrame,
        symbol: str
    ) -> pd.DataFrame:
        """
        1銘柄のOHLCを生成
        
        Args:
            df: 板情報DataFrame
            symbol: 銘柄コード
            
        Returns:
            OHLCDataFrame
        """
        # タイムスタンプカラムを確認
        ts_col = self._find_timestamp_column(df)
        if ts_col is None:
            raise ValueError(f"タイムスタンプカラムが見つかりません: {symbol}")
        
        # 板気配カラムを確認
        ask_px_col = self._find_column(df, ['最良売気配値1', '最良売気配値'])
        bid_px_col = self._find_column(df, ['最良買気配値1', '最良買気配値'])
        
        if not all([ask_px_col, bid_px_col]):
            raise ValueError(f"必要な板情報カラムが不足: {symbol}")
        
        # データコピー
        df = df.copy()
        
        # タイムスタンプをdatetimeに変換
        df['ts'] = pd.to_datetime(df[ts_col])
        df = df.dropna(subset=['ts']).sort_values('ts')
        
        # ミッド価格を計算（終値として使用）
        df['price'] = (
            df[ask_px_col].replace("", pd.NA).astype(float) +
            df[bid_px_col].replace("", pd.NA).astype(float)
        ) / 2.0
        df = df.dropna(subset=['price'])
        
        if len(df) == 0:
            # 空のDataFrameを返す
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol'])
        
        # 出来高（存在しない場合は0）
        volume_col = self._find_column(df, ['出来高', 'volume'])
        if volume_col:
            df['volume'] = df[volume_col].replace("", 0).fillna(0).astype(float)
        else:
            df['volume'] = 0
        
        # インデックスをタイムスタンプに設定
        df.set_index('ts', inplace=True)
        
        # リサンプリング
        ohlc = df['price'].resample(self.freq).ohlc()
        ohlc['volume'] = df['volume'].resample(self.freq).sum()
        ohlc['symbol'] = symbol
        
        # リセット
        ohlc = ohlc.reset_index()
        ohlc.rename(columns={'ts': 'timestamp'}, inplace=True)
        
        # 欠損除外
        ohlc = ohlc.dropna(subset=['open', 'high', 'low', 'close'])
        
        return ohlc
    
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
    
    # OHLC生成
    processor = OHLCProcessor(freq='1min')
    ohlc_data = processor.process(market_data)
    
    print(f"\n=== OHLC生成結果 ===")
    for symbol, df in list(ohlc_data.items())[:3]:
        print(f"\n{symbol}:")
        print(df.head())
        print(f"期間: {df['timestamp'].min()} ～ {df['timestamp'].max()}")
