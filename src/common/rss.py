import win32com.client      #エクセル用
import pandas as pd         #データフレーム用
import time                 #時間調整用
from enum import Enum, auto  # 列挙型用

# 抽象クラス
from abc import ABC, abstractmethod


# データ範囲用のデータクラス
from dataclasses import dataclass
@dataclass
class DataRange:
    start_row: int
    start_col: int
    end_row: int
    end_col: int

    def __post_init__(self):
        if self.start_row > self.end_row or self.start_col > self.end_col:
            raise ValueError("start_row must be less than or equal to end_row and start_col must be less than or equal to end_col")


class TickType(Enum):
    MIN1 = "1M"
    MIN2 = "2M"
    MIN3 = "3M"
    MIN4 = "4M"
    MIN5 = "5M"
    MIN10 = "10M"
    MIN15 = "15M"
    MIN30 = "30M"
    MIN60 = "60M"
    HOUR2 = "2H"
    HOUR4 = "4H"
    HOUR8 = "8H"
    DAY = "D"
    WEEK = "W"
    MONTH = "M"


class RssBase(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def create_formula(self) -> str:
        """
        抽象メソッド: RSS関数を作成する
        :param stock_code: 銘柄コード
        :param item: 取得したいデータの項目
        :return: RSS関数の文字列
        """
        pass

    @abstractmethod
    def get_dataframe(self) -> pd.DataFrame:
        """
        抽象メソッド: データフレームを取得する
        :return: pandas DataFrame
        """
        pass

    # 配信中かどうかを判定するメソッド
    @abstractmethod
    def is_valid(self) -> bool:
        """
        抽象メソッド: 配信中かどうかを判定する
        :return: True if valid, False otherwise
        """
        pass


class RssList(RssBase):
    def __init__(self, ws, stock_code: str, number: int, data_range: DataRange, header_row: int):
        """
        コンストラクタ
        :param ws: Excelのワークシートオブジェクト
        :param stock_code: 銘柄コード
        :param number: 取得するデータの数
        """
        self.ws = ws
        self.stock_code = stock_code
        self.number = number
        self.range = ws.Range(
            ws.Cells(data_range.start_row, data_range.start_col),
            ws.Cells(data_range.end_row, data_range.end_col)
        )
        self.data_range = data_range
        self.header_row = header_row

    def create_formula(self) -> str:
        """
        RSS関数を作成する
        :return: RSS関数の文字列
        """
        pass

    def is_valid(self) -> bool:
        """
        取得結果が有効かどうかを判定する（ステータスが「応答待ち」以外）
        :return: True if valid, False otherwise
        """
        try:
            status_str = self.ws.Cells(1, 1).Value
            status = status_str.split('=>')[-1].strip()
            return status != "応答待ち"
        except Exception as e:
            print(f"Error checking validity: {e}")
            return False

    def get_headers(self) -> list:
        """
        ヘッダーを取得する
        :return: ヘッダーのリスト
        """
        self.headers = [cell.Value for cell in self.ws.Range(
            self.ws.Cells(self.header_row, self.data_range.start_col),
            self.ws.Cells(self.header_row, self.data_range.end_col)
        )]
        return self.headers 

    def get_dataframe(self) -> pd.DataFrame:
        """
        データフレームを取得する
        :return: pandas DataFrame
        """
        formula = self.create_formula()
        print(f"RSS関数: {formula}")
        # シート全体をクリア
        self.ws.Cells.ClearContents()
        self.ws.Cells(1, 1).Formula = formula
        # ステータスが「応答待ち」以外になるまで待機
        while not self.is_valid():
            print("RSS関数のステータスが「応答待ち」以外になるまで待機中...")
            time.sleep(1)
        # データを取得
        headers = self.get_headers()
        data = self.range.Value

        df = pd.DataFrame(data, columns=headers)
        return df


class RssChart(RssList):
    def __init__(self, ws, stock_code: str, bar: str, number: int, data_range: DataRange, header_row: int):
        super().__init__(ws, stock_code, number, data_range, header_row)
        self.bar = bar

    def create_formula(self) -> str:
        return f'=RssChart(,"{self.stock_code}", "{self.bar}", {self.number})'


class RssTickList(RssList):
    def __init__(self, ws, stock_code: str, number: int, data_range: DataRange, header_row: int):
        super().__init__(ws, stock_code, number, data_range, header_row)

    def create_formula(self) -> str:
        return f'=RssTickList(,{self.stock_code}, {self.number})'


def main():
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")  # 今、開いている空白のブック
    except Exception as e:
        print("エクセルが開いていません。", e)
        return

    xl.Visible = True
    ws = xl.Worksheets('Sheet1')

    # 銘柄コード、足種、表示本数を設定
    stock_code = 7203  # トヨタ自動車の例
    bar = "D"  # 日足
    number = 50  # 表示本数
    header_row = 2
    rss_chart_range = DataRange(start_row=3, start_col=4, end_row=number + 2, end_col=10)

    rss_chart = RssChart(ws, stock_code, bar, number, rss_chart_range, header_row)
    df = rss_chart.get_dataframe()
    # データフレームを表示
    print(df)

    # ティッカーの取得
    rss_tick_list_range = DataRange(start_row=3, start_col=1, end_row=number + 2, end_col=3)
    rss_tick_list = RssTickList(ws, stock_code, number, rss_tick_list_range, header_row)
    tick_df = rss_tick_list.get_dataframe()
    # データフレームを表示
    print(tick_df)
    
if __name__ == "__main__":
    main()
# このコードは、RSSを使用して株価チャートを取得し、Excelに表示するサンプルです。