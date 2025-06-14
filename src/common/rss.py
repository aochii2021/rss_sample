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


class MarketStatusItem(Enum):
    stock_code = "銘柄コード"
    market_code = "市場コード"
    stock_name = "銘柄名称"
    market_name = "市場名称"
    market_division = "市場部名称"
    market_division_short = "市場部略称"
    current_date = "現在日付"
    current_price = "現在値"
    current_price_time = "現在値時刻"
    current_price_detail_time = "現在値詳細時刻"
    current_price_tick = "現在値ティック"
    current_price_flag = "現在値フラグ"
    prev_day_diff = "前日比"
    prev_day_diff_rate = "前日比率"
    prev_close = "前日終値"
    prev_date = "前日日付"
    prev_close_flag = "前日終値フラグ"
    ayumi1 = "歩み1"
    ayumi2 = "歩み2"
    ayumi3 = "歩み3"
    ayumi4 = "歩み4"
    ayumi1_detail_time = "歩み1詳細時刻"
    ayumi2_detail_time = "歩み2詳細時刻"
    ayumi3_detail_time = "歩み3詳細時刻"
    ayumi4_detail_time = "歩み4詳細時刻"
    volume = "出来高"
    trading_value = "売買代金"
    vwap = "出来高加重平均"
    market_cap = "時価総額"
    open = "始値"
    high = "高値"
    low = "安値"
    open_time = "始値時刻"
    high_time = "高値時刻"
    low_time = "安値時刻"
    open_detail_time = "始値詳細時刻"
    high_detail_time = "高値詳細時刻"
    low_detail_time = "安値詳細時刻"
    am_open = "前場始値"
    am_high = "前場高値"
    am_low = "前場安値"
    am_close = "前場終値"
    am_volume = "前場出来高"
    pm_open = "後場始値"
    pm_high = "後場高値"
    pm_low = "後場安値"
    am_open_time = "前場始値時刻"
    am_high_time = "前場高値時刻"
    am_low_time = "前場安値時刻"
    am_close_time = "前場終値時刻"
    am_volume_time = "前場出来高時刻"
    pm_open_time = "後場始値時刻"
    pm_high_time = "後場高値時刻"
    pm_low_time = "後場安値時刻"
    best_ask = "最良売気配値"
    best_bid = "最良買気配値"
    best_ask_qty = "最良売気配数量"
    best_bid_qty = "最良買気配数量"
    best_ask_time = "最良売気配時刻"
    best_bid_time = "最良買気配時刻"
    best_ask_detail_time = "最良売気配詳細時刻"
    best_bid_detail_time = "最良買気配詳細時刻"
    special_ask_flag = "特別売気配フラグ"
    special_bid_flag = "特別買気配フラグ"
    margin_type = "信用貸借区分"
    reverse_margin = "逆日歩"
    reverse_margin_update_date = "逆日歩更新日付"
    margin_sell = "信用売残"
    margin_sell_prev = "信用売残前週比"
    margin_buy = "信用買残"
    margin_buy_prev = "信用買残前週比"
    margin_ratio = "信用倍率"
    shoukin_update_date = "証金残更新日付"
    new_lending = "新規貸株"
    new_financing = "新規融資"
    repay_lending = "返済貸株"
    repay_financing = "返済融資"
    balance_lending = "残高貸株"
    balance_financing = "残高融資"
    balance_diff = "残高差引"
    prev_lending = "前日比貸株"
    prev_financing = "前日比融資"
    prev_diff = "前日比差引"
    turnover_days = "回転日数"
    lending_ratio = "貸借倍率"
    best_ask1 = "最良売気配値1"
    best_ask2 = "最良売気配値2"
    best_ask3 = "最良売気配値3"
    best_ask4 = "最良売気配値4"
    best_ask5 = "最良売気配値5"
    best_ask6 = "最良売気配値6"
    best_ask7 = "最良売気配値7"
    best_ask8 = "最良売気配値8"
    best_ask9 = "最良売気配値9"
    best_ask10 = "最良売気配値10"
    best_bid1 = "最良買気配値1"
    best_bid2 = "最良買気配値2"
    best_bid3 = "最良買気配値3"
    best_bid4 = "最良買気配値4"
    best_bid5 = "最良買気配値5"
    best_bid6 = "最良買気配値6"
    best_bid7 = "最良買気配値7"
    best_bid8 = "最良買気配値8"
    best_bid9 = "最良買気配値9"
    best_bid10 = "最良買気配値10"
    best_ask_qty1 = "最良売気配数量1"
    best_ask_qty2 = "最良売気配数量2"
    best_ask_qty3 = "最良売気配数量3"
    best_ask_qty4 = "最良売気配数量4"
    best_ask_qty5 = "最良売気配数量5"
    best_ask_qty6 = "最良売気配数量6"
    best_ask_qty7 = "最良売気配数量7"
    best_ask_qty8 = "最良売気配数量8"
    best_ask_qty9 = "最良売気配数量9"
    best_ask_qty10 = "最良売気配数量10"
    best_bid_qty1 = "最良買気配数量1"
    best_bid_qty2 = "最良買気配数量2"
    best_bid_qty3 = "最良買気配数量3"
    best_bid_qty4 = "最良買気配数量4"
    best_bid_qty5 = "最良買気配数量5"
    best_bid_qty6 = "最良買気配数量6"
    best_bid_qty7 = "最良買気配数量7"
    best_bid_qty8 = "最良買気配数量8"
    best_bid_qty9 = "最良買気配数量9"
    best_bid_qty10 = "最良買気配数量10"
    sell_market_qty = "売成行数量"
    buy_market_qty = "買成行数量"
    over_qty = "OVER気配数量"
    under_qty = "UNDER気配数量"
    unit_shares = "単位株数"
    dividend = "配当"
    dividend_ex_date = "配当落日"
    mid_dividend_ex_date = "中配落日"
    right_ex_date = "権利落日"
    settlement_date = "決算発表日"
    per = "PER"
    pbr = "PBR"
    base_price = "当日基準値"
    year_high = "年初来高値"
    year_low = "年初来安値"
    year_high_date = "年初来高値日付"
    year_low_date = "年初来安値日付"
    ipo_high = "上場来高値"
    ipo_low = "上場来安値"
    ipo_high_date = "上場来高値日付"
    ipo_low_date = "上場来安値日付"
    lending_rate = "貸株金利"
    lending_rate_date = "貸株金利適用日"


# ...existing code...

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
    def is_valid(self) -> bool:
        """
        抽象メソッド: 取得結果が有効かどうかを判定する
        :return: True if valid, False otherwise
        """
        pass


class RssMarket(RssBase):
    def __init__(self, ws, stock_code: str, item: MarketStatusItem):
        """
        コンストラクタ
        :param ws: Excelのワークシートオブジェクト
        :param stock_code: 銘柄コード
        :param item: 取得したいデータの項目
        """
        self.ws = ws
        self.stock_code = stock_code
        self.item = item

    def create_formula(self) -> str:
        return f'=RssMarket("{self.stock_code}", "{self.item.value}")'

    def is_valid(self):
        try:
            status = self.ws.Cells(1, 1).Value
            return status != ""
        except Exception as e:
            print(f"Error checking validity: {e}")
            return False

    def get_item(self):
        formula = self.create_formula()
        print(f"RSS関数: {formula}")
        # シート全体をクリア
        self.ws.Cells.ClearContents()
        self.ws.Cells(1, 1).Formula = formula
        # 取得結果が有効になるまで待機
        while not self.is_valid():
            print("RSS関数のステータスが有効になるまで待機中...")
            time.sleep(1)
        # データを取得
        item = self.ws.Cells(1, 1).Value
        if item is None:
            raise ValueError(f"RSS関数の結果が取得できませんでした: {self.stock_code}, {self.item.value}")
        return item


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


class RssTrendSma(RssList):
    def __init__(self, ws, stock_code: str, bar: str, number: int, data_range: DataRange, header_row: int,
                 window1: int = 5, window2: int = 25, window3: int = 75):
        super().__init__(ws, stock_code, number, data_range, header_row)
        self.bar = bar
        self.window1 = window1
        self.window2 = window2
        self.window3 = window3

    def create_formula(self) -> str:
        return f'=RssTrendSMA(,"{self.stock_code}", "{self.bar}", {self.number}, {self.window1}, {self.window2}, {self.window3})'


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