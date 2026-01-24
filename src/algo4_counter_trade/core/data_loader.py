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
        symbols: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        カットオフ日付以前のチャートデータを読み込み
        
        Args:
            cutoff_date: カットオフ日付（この日付より後のデータは読み込まない）
            lookback_days: 過去何営業日分のデータを読み込むか
            symbols: 対象銘柄リスト（Noneなら全銘柄）
            
        Returns:
            {銘柄コード: DataFrame} の辞書
            
        Raises:
            DataLeakError: 未来データが検出された場合
        """
        logger.info(f"チャートデータ読み込み: cutoff_date={cutoff_date.strftime('%Y-%m-%d')}")
        
        # 過去N営業日を取得
        target_dates = DateUtils.get_previous_business_days(cutoff_date, lookback_days)
        logger.info(f"対象期間: {lookback_days}営業日")
        for d in target_dates:
            logger.debug(f"  - {d.strftime('%Y-%m-%d')}")
        
        # チャートデータディレクトリを探索
        # 想定構造: chart_data/3M_3000_YYYYMMDD/stock_chart_3M_{symbol}_*.csv
        chart_data = {}
        
        for date_dir in self.chart_data_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            # ディレクトリ名から日付を抽出（例: 3M_3000_20260119）
            try:
                date_str = date_dir.name.split('_')[-1]  # 最後の部分が日付
                dir_date = datetime.strptime(date_str, '%Y%m%d')
            except (ValueError, IndexError):
                logger.debug(f"日付解析失敗: {date_dir.name}")
                continue
            
            # カットオフ日付より前のディレクトリのみ処理
            if dir_date >= cutoff_date:
                logger.debug(f"スキップ（未来データ）: {date_dir.name}")
                continue
            
            # 対象期間内のディレクトリのみ処理
            if dir_date not in target_dates:
                logger.debug(f"スキップ（期間外）: {date_dir.name}")
                continue
            
            logger.info(f"読み込み中: {date_dir.name}")
            
            # ディレクトリ内のCSVファイルを読み込み
            for csv_file in date_dir.glob("stock_chart_*.csv"):
                # ファイル名から銘柄コードを抽出
                # 例: stock_chart_3M_215A_20251208_20260119.csv
                try:
                    parts = csv_file.stem.split('_')
                    symbol = parts[3]  # stock_chart_3M_{symbol}_...
                except IndexError:
                    logger.warning(f"銘柄コード抽出失敗: {csv_file.name}")
                    continue
                
                # 銘柄フィルタリング
                if symbols is not None and symbol not in symbols:
                    continue
                
                # CSVファイル読み込み
                try:
                    df = self._read_csv_safe(csv_file)
                    
                    # タイムスタンプカラム確認
                    if 'timestamp' not in df.columns and '日付' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['日付'])
                    elif 'timestamp' not in df.columns:
                        logger.warning(f"タイムスタンプカラムなし: {csv_file.name}")
                        continue
                    
                    # データリークチェック
                    if self.validate_no_future_data:
                        valid, error_msg = DateUtils.validate_no_future_data(
                            df, cutoff_date, 'timestamp'
                        )
                        if not valid:
                            raise DataLeakError(error_msg)
                    
                    # データ範囲ログ
                    if self.log_data_range:
                        DateUtils.log_data_date_range(df, f"  {symbol}", 'timestamp')
                    
                    # 既存データに追加
                    if symbol in chart_data:
                        chart_data[symbol] = pd.concat([chart_data[symbol], df], ignore_index=True)
                    else:
                        chart_data[symbol] = df
                
                except Exception as e:
                    logger.error(f"ファイル読み込みエラー: {csv_file.name} - {e}")
                    continue
        
        # 各銘柄のデータを時系列でソート
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
        指定日の板情報データを読み込み
        
        Args:
            target_date: 対象日
            symbols: 対象銘柄リスト（Noneなら全銘柄）
            
        Returns:
            {銘柄コード: DataFrame} の辞書
        """
        logger.info(f"板情報データ読み込み: target_date={target_date.strftime('%Y-%m-%d')}")
        
        # 板情報ディレクトリを探索
        # 想定構造: market_order_book/YYYYMMDD/*.csv または market_order_book/YYYYMMDD_HHMM/*.csv
        date_str = target_date.strftime('%Y%m%d')
        market_data = {}
        
        # 日付に一致するディレクトリを探す
        matching_dirs = list(self.market_data_dir.glob(f"{date_str}*"))
        
        if not matching_dirs:
            logger.warning(f"板情報ディレクトリが見つかりません: {date_str}")
            return market_data
        
        for data_dir in matching_dirs:
            if not data_dir.is_dir():
                continue
            
            logger.info(f"読み込み中: {data_dir.name}")
            
            # ディレクトリ内のCSVファイルを読み込み
            csv_files = list(data_dir.glob("*.csv"))
            
            if not csv_files:
                logger.warning(f"CSVファイルが見つかりません: {data_dir.name}")
                continue
            
            for csv_file in csv_files:
                try:
                    df = self._read_csv_safe(csv_file)
                    
                    # タイムスタンプカラム確認・変換
                    ts_col = self._find_timestamp_column(df)
                    if ts_col is None:
                        logger.warning(f"タイムスタンプカラムなし: {csv_file.name}")
                        continue
                    
                    df['timestamp'] = pd.to_datetime(df[ts_col])
                    
                    # 銘柄コードカラム確認
                    symbol_col = '銘柄コード' if '銘柄コード' in df.columns else None
                    
                    if symbol_col is None:
                        # ファイル名から銘柄コード推測
                        symbol = csv_file.stem
                        df['銘柄コード'] = symbol
                    
                    # 銘柄ごとに分割
                    if symbol_col or '銘柄コード' in df.columns:
                        for symbol, group in df.groupby('銘柄コード'):
                            if pd.isna(symbol) or symbol == "":
                                continue
                            
                            # 銘柄フィルタリング
                            if symbols is not None and symbol not in symbols:
                                continue
                            
                            # データ範囲ログ
                            if self.log_data_range:
                                DateUtils.log_data_date_range(group, f"  {symbol}", 'timestamp')
                            
                            # 既存データに追加
                            if symbol in market_data:
                                market_data[symbol] = pd.concat([market_data[symbol], group], ignore_index=True)
                            else:
                                market_data[symbol] = group
                    
                except Exception as e:
                    logger.error(f"ファイル読み込みエラー: {csv_file.name} - {e}")
                    continue
        
        # 各銘柄のデータを時系列でソート
        for symbol in market_data:
            market_data[symbol] = market_data[symbol].sort_values('timestamp').reset_index(drop=True)
        
        logger.info(f"板情報データ読み込み完了: {len(market_data)}銘柄")
        return market_data
    
    def _read_csv_safe(self, file_path: Path) -> pd.DataFrame:
        """
        複数のエンコーディングを試してCSVを読み込み
        
        Args:
            file_path: CSVファイルパス
            
        Returns:
            DataFrame
        """
        encodings = ["utf-8-sig", "utf-8", "cp932", "shift-jis"]
        
        for encoding in encodings:
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                # エンコーディング以外のエラーは即座に発生
                raise
        
        # 全て失敗した場合はデフォルトで試行
        return pd.read_csv(file_path)
    
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
