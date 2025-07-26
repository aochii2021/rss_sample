# src/main.py
import sys
import os
import win32com.client
import pandas as pd
from dataclasses import fields
import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.rss import RssChart, RssTickList, DataRange, TickType
from common.data import StockCodeMaster
from common import common, columns

S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
# 出力ディレクトリの設定
S_OUTPUT_DIR = os.path.join(S_FILE_DIR, 'output')

def get_all_stock_charts(ws, tick_type: TickType, number: int, stock_code_master: StockCodeMaster):
    bar = tick_type.value  # 足種
    header_row = 2
    date_col = "日付"
    # 実行時日付（YYYYMMDD）
    exec_date = datetime.datetime.now().strftime('%Y%m%d')
    # フォルダ名生成: 足種_本数_実行時日付
    folder_name = f"{bar}_{number}_{exec_date}"
    output_dir = os.path.join(S_OUTPUT_DIR, folder_name)
    os.makedirs(output_dir, exist_ok=True)
    for stock_code in stock_code_master.get_all_codes():
        rss_chart_range = DataRange(start_row=3, start_col=4, end_row=number + 2, end_col=10)
        rss_chart = RssChart(ws, stock_code, bar, number, rss_chart_range, header_row)
        df = rss_chart.get_dataframe()
        print(f"df.columns: {df.columns}")  # デバッグ用
        if date_col in df.columns:
            start_date = df[date_col][0] if not df.empty else None
            end_date = df[date_col].iloc[-1] if not df.empty else None
            # 日付のスラッシュを削除
            start_date = start_date.replace('/', '') if start_date else None
            end_date = end_date.replace('/', '') if end_date else None
        else:
            start_date = end_date = None
        df["銘柄コード"] = stock_code  # 銘柄コードを追加
        print(f"銘柄コード: {stock_code}, 日付範囲: {start_date} - {end_date}")
        # CSVファイル名
        csv_file = os.path.join(output_dir, f"stock_chart_{bar}_{stock_code}_{start_date}_{end_date}.csv")
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

    # 銘柄コードマスターの読み込み
    stock_code_master = StockCodeMaster()
    stock_code_master.load()
    # 銘柄コードの一覧を表示
    print("銘柄コード一覧:")
    print(stock_code_master.get_all_codes())

    # 全銘柄のチャートを取得
    # get_all_stock_charts(ws, TickType.MIN1, 3000, stock_code_master)
    # get_all_stock_charts(ws, TickType.MIN5 , 3000, stock_code_master)
    # get_all_stock_charts(ws, TickType.DAY, 730, stock_code_master) # 730日(約2年)分のデータを取得
    get_all_stock_charts(ws, TickType.WEEK, 104, stock_code_master) # 104週(約2年)分のデータを取得
    # get_all_stock_charts(ws, TickType.MONTH, 100, stock_code_master)

    # # ティッカーの取得
    # rss_tick_list_range = DataRange(start_row=3, start_col=1, end_row=number + 2, end_col=3)
    # rss_tick_list = RssTickList(ws, stock_code, number, rss_tick_list_range, header_row)
    # tick_df = rss_tick_list.get_dataframe()
    # # データフレームを表示
    # print(tick_df)


if __name__ == "__main__":
    main()