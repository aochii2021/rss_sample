# src/main.py
import sys
import os
import win32com.client
import pandas as pd
from dataclasses import fields

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.rss import RssMarket, MarketStatusItem, DataRange
from common.data import StockCodeMaster
from common import common, columns

S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
# 出力ディレクトリの設定
S_OUTPUT_DIR = os.path.join(S_FILE_DIR, 'output')


def get_rss_market(ws, stock_code: str, item_list: list[MarketStatusItem]) -> str:
    """
    RSSマーケットデータを取得する
    :param ws: Excelワークシートオブジェクト
    :param stock_code: 銘柄コード
    :param header_row: ヘッダ行の行番号
    :return: 取得したデータの値
    """
    print(f"銘柄コード: {stock_code}, 項目: {item_list}")
    rss = RssMarket(ws, [stock_code], item_list)
    item_value = rss.get_dataframe()
    return item_value


def get_all_rss_market(ws, stock_code_list: list[str], item_list: list[MarketStatusItem]) -> pd.DataFrame:
    """
    全銘柄のRSSマーケットデータを取得する
    :param ws: Excelワークシートオブジェクト
    :param stock_code_list: 銘柄コードのリスト
    :param item_list: 取得したいマーケットステータスの項目
    :return: 取得したデータのDataFrame
    """
    print(f"銘柄コードリスト: {stock_code_list}, 項目: {item_list}")
    rss = RssMarket(ws, stock_code_list, item_list)
    df = rss.get_dataframe()
    return df


def main():
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")  # 今、開いている空白のブック
    except Exception as e:
        print("エクセルが開いていません。", e)
        return

    xl.Visible = True
    ws = xl.Worksheets('Sheet1')

    # market_status_item_list = [  # 取得したいマーケットステータスの項目
    #     MarketStatusItem.STOCK_CODE,
    #     MarketStatusItem.CURRENT_PRICE,
    #     MarketStatusItem.PREV_DAY_DIFF,
    #     MarketStatusItem.PER,
    #     MarketStatusItem.PBR,
    #     MarketStatusItem.VOLUME,
    # ]
    market_status_item_list = [
        item for item in MarketStatusItem  # 全てのマーケットステータス項目を取得
    ]
    # print(f"取得するマーケットステータス項目: {market_status_item_list}")

    # 銘柄コードマスターの読み込み
    stock_code_master = StockCodeMaster()
    stock_code_master.load()
    # 銘柄コードの一覧を表示
    stock_code_list = stock_code_master.get_all_codes()
    # stock_code_list = [
    #     "7203",  # トヨタ自動車
    #     "6758",  # ソニーグループ
    # ]
    print("銘柄コード一覧:")
    for code in stock_code_list:
        print(f" - {code}")
    # 全銘柄のマーケットデータを取得
    df = get_all_rss_market(ws, stock_code_list, market_status_item_list)
    print("全銘柄のマーケットデータ:")
    print(df.head())  # 最初の5行を表示
    # save DataFrame to csv file
    output_file = os.path.join(S_OUTPUT_DIR, 'rss_market_data.csv')
    df.to_csv(output_file, index=False)
    print(f"データをCSVファイルに保存しました: {output_file}")


if __name__ == "__main__":
    main()