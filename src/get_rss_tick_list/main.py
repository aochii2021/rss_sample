# src/main.py
import sys
import os
import win32com.client
import pandas as pd
from dataclasses import fields

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.rss import RssTickList, DataRange, TickType
from common.data import StockCodeMaster
from common import common, columns

S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
# 出力ディレクトリの設定
S_OUTPUT_DIR = os.path.join(S_FILE_DIR, 'output')

def get_stock_tick_list(ws, number: int, stock_code: str, rss_tick_list_range: DataRange, header_row: int):
    """
    銘柄コードのティックリストを取得し、DataFrameとして返す
    """
    rss_tick_list = RssTickList(ws, stock_code, number, rss_tick_list_range, header_row)
    df = rss_tick_list.get_dataframe()
    print(f"df.columns: {df.columns}")  # デバッグ用
    return df

def get_all_stock_tick_list(ws, tick_type: TickType, number: int, stock_code_master: StockCodeMaster):
    bar = tick_type.value  # 足種
    header_row = 2
    # データクラスからカラム名を取得
    date_col = "日付"
    rss_tick_list_range = DataRange(start_row=3, start_col=1, end_row=number + 2, end_col=3)
    for stock_code in stock_code_master.get_all_codes():
        df = get_stock_tick_list(ws, number, stock_code, rss_tick_list_range, header_row)
        if date_col in df.columns:
            start_date = df[date_col][0] if not df.empty else None
            end_date = df[date_col].iloc[-1] if not df.empty else None
            # 日付のスラッシュを削除
            start_date = start_date.replace('/', '') if start_date else None
            end_date = end_date.replace('/', '') if end_date else None
        else:
            start_date = end_date = None
        print(f"銘柄コード: {stock_code}, 日付範囲: {start_date} - {end_date}")
        # save DataFrame to csv file
        csv_file = os.path.join(S_OUTPUT_DIR, f"stock_chart_{bar}_{stock_code}_{start_date}_{end_date}.csv")
        print(csv_file)
        df.to_csv(csv_file, index=False)
        print(f"Saved: {csv_file}")

def main():
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")  # 今、開いている空白のブック
    except Exception as e:
        print("エクセルが開いていません。", e)
        return

    xl.Visible = True
    ws = xl.Worksheets('Sheet1')

    # トヨタ自動車のティックリストを取得
    stock_code = 7203  # トヨタ自動車の銘柄コード
    number = 300
    header_row = 2
    rss_tick_list_range = DataRange(start_row=3, start_col=1, end_row=number + 2, end_col=3)
    df = get_stock_tick_list(ws, number, stock_code, rss_tick_list_range, header_row)
    print(f"ティックリスト for {stock_code}:")
    print(df)


if __name__ == "__main__":
    main()