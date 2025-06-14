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


def get_rss_market(ws, stock_code: str, item_list: list[MarketStatusItem], header_row: int = 2) -> str:
    """
    RSSマーケットデータを取得する
    :param ws: Excelワークシートオブジェクト
    :param stock_code: 銘柄コード
    :param header_row: ヘッダ行の行番号
    :return: 取得したデータの値
    """
    print(f"銘柄コード: {stock_code}, 項目: {item_list}")
    rss = RssMarket(ws, stock_code, item_list)
    item_value = rss.get_item()
    return item_value


def main():
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")  # 今、開いている空白のブック
    except Exception as e:
        print("エクセルが開いていません。", e)
        return

    xl.Visible = True
    ws = xl.Worksheets('Sheet1')

    stock_code = "7203"  # 例: トヨタ自動車の銘柄コード
    market_status_item_list = [  # 取得したいマーケットステータスの項目
        MarketStatusItem.market_code,
        MarketStatusItem.current_price,
        MarketStatusItem.prev_day_diff
    ]
    item = get_rss_market(ws, stock_code, market_status_item_list)
    print(f"取得したデータ: {item}")


if __name__ == "__main__":
    main()