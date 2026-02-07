"""
データローダーモジュール
チャートデータと板情報データの読み込みを管理（データリーク防止機能付き）
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.date_utils import DateUtils

logger = logging.getLogger(__name__)


class DataLeakError(Exception):
    """データリーク検出エラー"""
    pass


class DataLoader:
    """
    データ読み込みクラス（データリーク防止機能付き）
    
    全てのデータ読み込みで、指定されたcutoff_date以降のデータが
    含まれていないことを保証します。
    """
    
    def __init__(
        self,
        chart_data_dir: str,
        market_data_dir: str,
        validate_no_future_data: bool = True,
        log_data_range: bool = True
    ):
        """
        初期化
        
        Args:
            chart_data_dir: チャートデータディレクトリ
            market_data_dir: 板情報ディレクトリ
            validate_no_future_data: 未来データ混入チェックを有効化
            log_data_range: データ期間をログ出力
        """
        self.chart_data_dir = Path(chart_data_dir)
        self.market_data_dir = Path(market_data_dir)
        self.validate_no_future_data = validate_no_future_data
        self.log_data_range = log_data_range
        
        if not self.chart_data_dir.exists():
            raise FileNotFoundError(f"チャートデータディレクトリが存在しません: {self.chart_data_dir}")
        if not self.market_data_dir.exists():
            raise FileNotFoundError(f"板情報ディレクトリが存在しません: {self.market_data_dir}")
    
    def load_chart_data_until(
        self,
        cutoff_date: datetime,
        lookback_days: int = 5,
        symbols: Optional[List[str]] = None,
        allowed_timeframes: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        集約CSV（all_3M.csv, all_D.csv等）からチャートデータを読み込む
        Args/Returns/Raisesは従来通り
        """
        logger.info(f"チャートデータ読み込み: cutoff_date={cutoff_date.strftime('%Y-%m-%d')}")
        target_dates = DateUtils.get_previous_business_days(cutoff_date, lookback_days)
        logger.info(f"対象期間: {lookback_days}営業日")
        for d in target_dates:
            logger.debug(f"  - {d.strftime('%Y-%m-%d')}")

        # 集約CSVファイルを全て探索
        chart_data = {}
        for csv_file in self.chart_data_dir.glob("all_*.csv"):
            # タイムフレーム判定
            parts = csv_file.stem.split('_')
            timeframe = parts[1] if len(parts) >= 2 else None
            if allowed_timeframes is not None and timeframe not in allowed_timeframes:
                logger.debug(f"タイムフレーム除外: {csv_file.name}")
                continue
            try:
                df = self._read_csv_safe(csv_file)
                # 必須カラム: 'timestamp', 'symbol' or '銘柄コード'
                if 'timestamp' not in df.columns:
                    # 日付+時刻から生成
                    if '日付' in df.columns:
                        if '時刻' in df.columns:
                            df['timestamp'] = pd.to_datetime(
                                df['日付'].astype(str) + ' ' + df['時刻'].fillna('00:00')
                            )
                        else:
                            df['timestamp'] = pd.to_datetime(df['日付'])
                    else:
                        logger.warning(f"タイムスタンプカラムなし: {csv_file.name}")
                        continue
                # 銘柄コード正規化
                if 'symbol' not in df.columns:
                    if '銘柄コード' in df.columns:
                        df['symbol'] = df['銘柄コード']
                    else:
                        logger.warning(f"銘柄コードカラムなし: {csv_file.name}")
                        continue
                # カラム名正規化
                column_mapping = {
                    '始値': 'open',
                    '高値': 'high',
                    '安値': 'low',
                    '終値': 'close',
                    '出来高': 'volume'
                }
                df.rename(columns=column_mapping, inplace=True)
                price_cols = ['open', 'high', 'low', 'close']
                for col in price_cols + ['volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                if set(price_cols).issubset(df.columns):
                    df = df[df[price_cols].notna().any(axis=1)]
                if 'volume' in df.columns:
                    df['volume'] = df['volume'].fillna(0)
                # 日付・銘柄フィルタ
                df = df[df['timestamp'] < cutoff_date]
                df = df[df['timestamp'].dt.normalize().isin([d.date() for d in target_dates])]
                if symbols is not None:
                    df = df[df['symbol'].isin(symbols)]
                # データリークチェック
                if self.validate_no_future_data:
                    valid, error_msg = DateUtils.validate_no_future_data(
                        df, cutoff_date, 'timestamp'
                    )
                    if not valid:
                        raise DataLeakError(error_msg)
                # データ範囲ログ
                if self.log_data_range:
                    for symbol, group in df.groupby('symbol'):
                        DateUtils.log_data_date_range(group, f"  {symbol}", 'timestamp')
                # 銘柄ごとに格納
                for symbol, group in df.groupby('symbol'):
                    if symbol in chart_data:
                        chart_data[symbol] = pd.concat([chart_data[symbol], group], ignore_index=True)
                    else:
                        chart_data[symbol] = group.reset_index(drop=True)
            except Exception as e:
                logger.error(f"集約CSV読み込みエラー: {csv_file.name} - {e}")
                continue
        # ソート
        for symbol in chart_data:
            chart_data[symbol] = chart_data[symbol].sort_values('timestamp').reset_index(drop=True)
        logger.info(f"チャートデータ読み込み完了: {len(chart_data)}銘柄")
        return chart_data
    
    def load_market_data_for_date(
        self,
        target_date: datetime,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        集約CSV（all_market_order_book.csv）から板情報データを読み込む
        Args/Returnsは従来通り
        """
        logger.info(f"板情報データ読み込み: target_date={target_date.strftime('%Y-%m-%d')}")
        market_data = {}
        for csv_file in self.market_data_dir.glob("all_*.csv"):
            try:
                df = self._read_csv_safe(csv_file)
                # タイムスタンプカラム
                ts_col = self._find_timestamp_column(df)
                if ts_col is None:
                    logger.warning(f"タイムスタンプカラムなし: {csv_file.name}")
                    continue
                df['timestamp'] = pd.to_datetime(df[ts_col])
                # 銘柄コード正規化
                if 'symbol' not in df.columns:
                    if '銘柄コード' in df.columns:
                        df['symbol'] = df['銘柄コード']
                    else:
                        logger.warning(f"銘柄コードカラムなし: {csv_file.name}")
                        continue
                # カラム名正規化
                column_mapping = {
                    '始値': 'open',
                    '高値': 'high',
                    '安値': 'low',
                    '終値': 'close',
                    '出来高': 'volume'
                }
                df.rename(columns=column_mapping, inplace=True)
                # 日付・銘柄フィルタ（date型同士で比較）
                date_only = target_date.date()
                df = df[df['timestamp'].dt.date == date_only]
                if symbols is not None:
                    df = df[df['symbol'].isin(symbols)]
                # trade_date列を追加（EnvironmentFilterで使用）
                df['trade_date'] = target_date.strftime('%Y-%m-%d')
                # データ範囲ログ
                if self.log_data_range:
                    for symbol, group in df.groupby('symbol'):
                        DateUtils.log_data_date_range(group, f"  {symbol}", 'timestamp')
                # 銘柄ごとに格納
                for symbol, group in df.groupby('symbol'):
                    if symbol in market_data:
                        market_data[symbol] = pd.concat([market_data[symbol], group], ignore_index=True)
                    else:
                        market_data[symbol] = group.reset_index(drop=True)
            except Exception as e:
                logger.error(f"集約CSV読み込みエラー: {csv_file.name} - {e}")
                continue
        # ソート
        for symbol in market_data:
            market_data[symbol] = market_data[symbol].sort_values('timestamp').reset_index(drop=True)
        logger.info(f"板情報データ読み込み完了: {len(market_data)}銘柄")
        return market_data
    
    def _read_csv_safe(self, file_path: Path) -> pd.DataFrame:
        """
        複数のエンコーディングを試してCSVを読み込み、銘柄コードカラムをstr型で強制
        Args:
            file_path: CSVファイルパス
        Returns:
            DataFrame
        """
        encodings = ["utf-8-sig", "utf-8", "cp932", "shift-jis"]
        dtype_dict = {"銘柄コード": str, "symbol": str}
        for encoding in encodings:
            try:
                return pd.read_csv(file_path, encoding=encoding, dtype=dtype_dict)
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                # エンコーディング以外のエラーは即座に発生
                raise
        # 全て失敗した場合はデフォルトで試行
        return pd.read_csv(file_path, dtype=dtype_dict)
    
    def _find_timestamp_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        タイムスタンプカラムを探す
        
        Args:
            df: DataFrame
            
        Returns:
            タイムスタンプカラム名（見つからない場合はNone）
        """
        candidates = [
            'timestamp', 'ts',
            '記録日時', '現在値詳細時刻', '現在値時刻',
            '日時', '日付'
        ]
        
        for col in candidates:
            if col in df.columns:
                return col
        
        return None


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    loader = DataLoader(
        chart_data_dir="input/chart_data",
        market_data_dir="input/market_order_book"
    )
    
    # 2026-01-20のデータを読み込み（2026-01-19以前のチャートデータ）
    target_date = datetime(2026, 1, 20)
    
    print(f"\n=== チャートデータ読み込みテスト ===")
    chart_data = loader.load_chart_data_until(target_date, lookback_days=5)
    print(f"読み込み銘柄数: {len(chart_data)}")
    for symbol, df in list(chart_data.items())[:3]:
        print(f"  {symbol}: {len(df)}行")
    
    print(f"\n=== 板情報データ読み込みテスト ===")
    market_data = loader.load_market_data_for_date(target_date)
    print(f"読み込み銘柄数: {len(market_data)}")
    for symbol, df in list(market_data.items())[:3]:
        print(f"  {symbol}: {len(df)}行")
