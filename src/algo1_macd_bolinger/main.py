# src/main.py
import sys
import os
import win32com.client
import pandas as pd
from dataclasses import fields

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.rss import (
    RssChart,
    RssTickList,
    RssOrderIDList,
    RssMarginOpenOrder,
    DataRange,
    TickType,
    MarginOpenOrderParam,
    MarginCloseOrderParam,
    OrderTrigger,
    BuySellType,
    OrderType,
    SorType,
    MarginType,
    PriceType,
    ExecutionCondition,
    AccountType,
)
from common.data import StockCodeMaster
from common import common, columns

S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
# 出力ディレクトリの設定
S_OUTPUT_DIR = os.path.join(S_FILE_DIR, 'output')

default_margin_open_order = MarginOpenOrderParam(
    order_id=6,
    order_trigger=OrderTrigger.TRUE,
    stock_code="7203.T",
    buy_sell_type=BuySellType.BUY,
    order_type=OrderType.NORMAL,
    sor_type=SorType.NORMAL,
    margin_type=MarginType.GENERAL_ONE_DAY,
    order_quantity=100,
    price_type=PriceType.MARKET,
    order_price=None,
    execution_condition=ExecutionCondition.TODAY,
    account_type=AccountType.SPECIFIC
)


def sample_margin_open_order(ws):
    # 新規注文用インスタンス
    rss_margin_open_order = RssMarginOpenOrder(ws, default_margin_open_order)
    print("Create formula")
    print(rss_margin_open_order.create_formula())
    # 新規注文実行
    if rss_margin_open_order.execute():
        print("新規注文が成功しました。")
    else:
        print("新規注文が失敗しました。")

def main():
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")  # 今、開いている空白のブック
    except Exception as e:
        print("エクセルが開いていません。", e)
        return

    xl.Visible = True
    ws = xl.Worksheets('Sheet1')

    # 注文ID取得
    rss_order_id_list = RssOrderIDList(ws)
    # order_id_list = rss_order_id_list.get_dataframe()
    # print("注文IDリスト:", order_id_list)
    next_order_id = rss_order_id_list.get_next_order_id()
    print("次の注文ID:", next_order_id)

    # 新規注文
    # sample_margin_open_order(ws)

    # 返済注文
    # sample_margin_close_order(ws)


if __name__ == "__main__":
    main()