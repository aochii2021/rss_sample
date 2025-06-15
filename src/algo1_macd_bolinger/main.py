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
    order_id=1,
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


def main():
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")  # 今、開いている空白のブック
    except Exception as e:
        print("エクセルが開いていません。", e)
        return

    xl.Visible = True
    ws = xl.Worksheets('Sheet1')

    # 注文用インスタンス
    rss_margin_open_order = RssMarginOpenOrder(ws, default_margin_open_order)
    print("Create formula")
    print(rss_margin_open_order.create_formula())


if __name__ == "__main__":
    main()