# src/main.py
import sys
import os
import win32com.client
import pandas as pd
from dataclasses import fields

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.rss import RssTrendSma, DataRange, TickType
from common.data import StockCodeMaster
from common import common, columns

S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
# 出力ディレクトリの設定
S_OUTPUT_DIR = os.path.join(S_FILE_DIR, 'output')

def get_one_trend_sma(ws,
                      stock_code: str,
                      bar: str,
                      number: int,
                      header_row: int = 2) -> pd.DataFrame:
    # データクラスからカラム名を取得
    rss_chart_range = DataRange(start_row=3, start_col=4, end_row=number + 2, end_col=10)
    rss_chart = RssTrendSma(ws, stock_code, bar, number, rss_chart_range, header_row)
    df = rss_chart.get_dataframe()
    return df

def get_all_trends_sma(ws, bar: str, number: int, stock_code_master: StockCodeMaster):
    header_row = 2
    # データクラスからカラム名を取得
    date_col = "日付"
    for stock_code in stock_code_master.get_all_codes():
        df = get_one_trend_sma(ws, stock_code, bar, number, header_row)
        if df.empty:
            print(f"銘柄コード: {stock_code} のデータが取得できませんでした。")
            continue
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
        csv_file = os.path.join(S_OUTPUT_DIR, f"stock_trends_sma_{bar}_{stock_code}_{start_date}_{end_date}.csv")
        df.to_csv(csv_file, index=False)

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
    get_all_trends_sma(ws, TickType.MIN1.value, 2000, stock_code_master)
    get_all_trends_sma(ws, TickType.MIN3.value, 2000, stock_code_master)
    get_all_trends_sma(ws, TickType.MIN5.value, 2000, stock_code_master)
    get_all_trends_sma(ws, TickType.DAY.value, 2000, stock_code_master)
    get_all_trends_sma(ws, TickType.WEEK.value, 2000, stock_code_master)


if __name__ == "__main__":
    main()