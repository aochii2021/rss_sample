# src/main.py
import sys
import os
import win32com.client
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.rss import RssChart, RssTickList, DataRange
from common.data import StockCodeMaster

def main():
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")  # 今、開いている空白のブック
    except Exception as e:
        print("エクセルが開いていません。", e)
        return

    xl.Visible = True
    ws = xl.Worksheets('Sheet1')

    # 銘柄コードマスターの読み込み
    stock_code_master = StockCodeMaster()
    stock_code_master.load()
    # 銘柄コードの一覧を表示
    print("銘柄コード一覧:")
    print(stock_code_master.get_all_codes())

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