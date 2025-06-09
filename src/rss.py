import win32com.client      #エクセル用
import pandas as pd         #データフレーム用

# 抽象クラス
from abc import ABC, abstractmethod

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


class RssChart(RssBase):
    def __init__(self, ws, stock_code: str, bar: str, number: int):
        """
        コンストラクタ
        :param ws: Excelのワークシートオブジェクト
        :param stock_code: 銘柄コード
        :param bar: チャートの種類（例：日足、週足など）
        :param number: 取得するデータの数
        """
        self.ws = ws
        self.stock_code = stock_code
        self.bar = bar
        self.number = number

    def create_formula(self) -> str:
        """
        RSS関数を作成する
        :return: RSS関数の文字列
        """
        return f'=RssChart("{self.stock_code}", "{self.bar}", {self.number})'

    def get_dataframe(self) -> pd.DataFrame:
        """
        データフレームを取得する
        :return: pandas DataFrame
        """
        formula = self.create_formula()
        self.ws.Cells(1, 1).Formula = formula
        data = self.ws.Range(self.ws.Cells(3, 4), self.ws.Cells(self.number + 2, 10)).Value
        df = pd.DataFrame(data, columns=["date", "time", "Open", "High", "Low", "Close", "Volume"])
        df["date"] = pd.to_datetime(df["date"] + " " + df["time"])
        df.set_index("date", inplace=True)
        return df


def main():
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")  # 今、開いている空白のブック
    except Exception as e:
        print("エクセルが開いていません。", e)
        return

    xl.Visible = True
    ws = xl.Worksheets('Sheet1')

    # 銘柄コード、足種、表示本数を設定
    stock_code = "7203.T"  # トヨタ自動車の例
    bar = "D"  # 日足
    number = 50  # 表示本数

    rss_chart = RssChart(ws, stock_code, bar, number)
    df = rss_chart.get_dataframe()
    
    print(df)


if __name__ == "__main__":
    main()
# このコードは、RSSを使用して株価チャートを取得し、Excelに表示するサンプルです。