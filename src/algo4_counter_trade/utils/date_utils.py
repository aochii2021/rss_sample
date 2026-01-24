"""
日付・時刻ユーティリティモジュール
営業日計算、lookback処理、時刻フィルタリング機能を提供
"""
from datetime import datetime, timedelta, time
from typing import List, Optional, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DateUtils:
    """日付・時刻処理ユーティリティ"""
    
    # 日本の祝日（簡易版、実運用ではjpholidayライブラリ推奨）
    JP_HOLIDAYS_2026 = [
        "2026-01-01",  # 元日
        "2026-01-12",  # 成人の日
        "2026-02-11",  # 建国記念の日
        "2026-03-20",  # 春分の日
        "2026-04-29",  # 昭和の日
        "2026-05-03",  # 憲法記念日
        "2026-05-04",  # みどりの日
        "2026-05-05",  # こどもの日
        "2026-07-20",  # 海の日
        "2026-08-11",  # 山の日
        "2026-09-21",  # 敬老の日
        "2026-09-22",  # 秋分の日
        "2026-10-12",  # スポーツの日
        "2026-11-03",  # 文化の日
        "2026-11-23",  # 勤労感謝の日
    ]
    
    @staticmethod
    def is_business_day(date: datetime) -> bool:
        """
        営業日（平日かつ非祝日）判定
        
        Args:
            date: 判定する日付
            
        Returns:
            営業日ならTrue
        """
        # 土日チェック
        if date.weekday() >= 5:  # 5=土曜, 6=日曜
            return False
        
        # 祝日チェック（簡易）
        date_str = date.strftime('%Y-%m-%d')
        if date_str in DateUtils.JP_HOLIDAYS_2026:
            return False
        
        return True
    
    @staticmethod
    def get_previous_business_days(date: datetime, n_days: int) -> List[datetime]:
        """
        指定日付の過去N営業日を取得
        
        Args:
            date: 基準日
            n_days: 取得する営業日数
            
        Returns:
            過去N営業日のリスト（降順：最新→古い順）
        """
        business_days = []
        current_date = date - timedelta(days=1)  # 基準日の前日から開始
        
        while len(business_days) < n_days:
            if DateUtils.is_business_day(current_date):
                business_days.append(current_date)
            current_date -= timedelta(days=1)
        
        return business_days
    
    @staticmethod
    def get_next_business_days(date: datetime, n_days: int) -> List[datetime]:
        """
        指定日付の翌営業日以降N営業日を取得
        
        Args:
            date: 基準日
            n_days: 取得する営業日数
            
        Returns:
            翌営業日以降N営業日のリスト（昇順）
        """
        business_days = []
        current_date = date + timedelta(days=1)  # 基準日の翌日から開始
        
        while len(business_days) < n_days:
            if DateUtils.is_business_day(current_date):
                business_days.append(current_date)
            current_date += timedelta(days=1)
        
        return business_days
    
    @staticmethod
    def get_business_days_between(start_date: datetime, end_date: datetime) -> List[datetime]:
        """
        開始日と終了日の間の全営業日を取得
        
        Args:
            start_date: 開始日（含む）
            end_date: 終了日（含む）
            
        Returns:
            営業日のリスト（昇順）
        """
        business_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if DateUtils.is_business_day(current_date):
                business_days.append(current_date)
            current_date += timedelta(days=1)
        
        return business_days
    
    @staticmethod
    def filter_trading_hours(
        df: pd.DataFrame,
        morning_start: str = "09:00",
        morning_end: str = "11:30",
        afternoon_start: str = "12:30",
        afternoon_end: str = "15:00",
        time_column: str = 'timestamp'
    ) -> pd.DataFrame:
        """
        取引時間内のデータのみフィルタリング
        
        Args:
            df: データフレーム
            morning_start: 前場開始時刻
            morning_end: 前場終了時刻
            afternoon_start: 後場開始時刻
            afternoon_end: 後場終了時刻
            time_column: 時刻カラム名
            
        Returns:
            フィルタリング後のデータフレーム
        """
        df = df.copy()
        
        # タイムスタンプをdatetimeに変換
        if not pd.api.types.is_datetime64_any_dtype(df[time_column]):
            df[time_column] = pd.to_datetime(df[time_column])
        
        # 時刻を抽出
        df['time_only'] = df[time_column].dt.time
        
        # 時刻オブジェクト作成
        morning_start_time = time.fromisoformat(morning_start)
        morning_end_time = time.fromisoformat(morning_end)
        afternoon_start_time = time.fromisoformat(afternoon_start)
        afternoon_end_time = time.fromisoformat(afternoon_end)
        
        # フィルタリング
        mask = (
            ((df['time_only'] >= morning_start_time) & (df['time_only'] <= morning_end_time)) |
            ((df['time_only'] >= afternoon_start_time) & (df['time_only'] <= afternoon_end_time))
        )
        
        filtered_df = df[mask].drop(columns=['time_only']).copy()
        
        logger.debug(
            f"取引時間フィルタリング: {len(df)}件 → {len(filtered_df)}件 "
            f"({len(df) - len(filtered_df)}件除外)"
        )
        
        return filtered_df
    
    @staticmethod
    def validate_no_future_data(
        df: pd.DataFrame,
        cutoff_date: datetime,
        date_column: str = 'timestamp'
    ) -> Tuple[bool, Optional[str]]:
        """
        未来データ混入チェック
        
        Args:
            df: データフレーム
            cutoff_date: カットオフ日付（この日付より後のデータがあればNG）
            date_column: 日付カラム名
            
        Returns:
            (検証結果, エラーメッセージ)
            検証OKならTrue, エラーがあればFalse
        """
        if df.empty:
            return True, None
        
        # 日付カラムをdatetimeに変換
        if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
            df = df.copy()
            df[date_column] = pd.to_datetime(df[date_column])
        
        # 最大日付を取得
        max_date = df[date_column].max()
        
        if max_date > cutoff_date:
            error_msg = (
                f"未来データが検出されました: "
                f"カットオフ日付={cutoff_date.strftime('%Y-%m-%d')}, "
                f"データ最大日付={max_date.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            logger.error(error_msg)
            return False, error_msg
        
        logger.debug(
            f"未来データチェックOK: データ範囲={df[date_column].min()} ～ {max_date}, "
            f"カットオフ={cutoff_date}"
        )
        return True, None
    
    @staticmethod
    def log_data_date_range(
        df: pd.DataFrame,
        data_name: str,
        date_column: str = 'timestamp'
    ) -> None:
        """
        データの日付範囲をログ出力
        
        Args:
            df: データフレーム
            data_name: データ名（ログ出力用）
            date_column: 日付カラム名
        """
        if df.empty:
            logger.info(f"{data_name}: データなし")
            return
        
        # 日付カラムをdatetimeに変換
        if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
            df = df.copy()
            df[date_column] = pd.to_datetime(df[date_column])
        
        min_date = df[date_column].min()
        max_date = df[date_column].max()
        
        logger.info(
            f"{data_name}: {len(df)}件, "
            f"期間={min_date.strftime('%Y-%m-%d %H:%M:%S')} ～ "
            f"{max_date.strftime('%Y-%m-%d %H:%M:%S')}"
        )


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    # 営業日判定テスト
    test_date = datetime(2026, 1, 20)  # 火曜日
    print(f"{test_date.strftime('%Y-%m-%d')}: 営業日={DateUtils.is_business_day(test_date)}")
    
    # 過去5営業日取得テスト
    prev_days = DateUtils.get_previous_business_days(test_date, 5)
    print(f"過去5営業日: {[d.strftime('%Y-%m-%d') for d in prev_days]}")
    
    # バックテスト期間の営業日取得テスト
    start = datetime(2026, 1, 19)
    end = datetime(2026, 1, 23)
    business_days = DateUtils.get_business_days_between(start, end)
    print(f"バックテスト期間の営業日: {[d.strftime('%Y-%m-%d') for d in business_days]}")
