# src/main.py
import win32com.client
import time
from openpyxl import Workbook

# Excelの起動
xl = win32com.client.Dispatch("Excel.Application")
xl.Visible = True
wb = Workbook()
ws = wb.active

# RSSから取得するデータの設定
rss_list = ['銘柄名称', '現在値', '時価総額', '配当', 'PER', 'PBR']
ws.append(['市場コード'] + rss_list)

# 銘柄コードの設定
stock_codes = ['7203.T', '6758.T']  # トヨタ自動車とソニーグループの例

for stock_code in stock_codes:
    row = [stock_code]
    for item in rss_list:
        try:
            formula = f'=RssMarket("{stock_code}", "{item}")'
            row.append(formula)
        except Exception as e:
            print(f"Error retrieving data for {stock_code}: {e}")
    ws.append(row)
    time.sleep(1)  # データ取得間隔

# Excelファイルの保存
wb.save("株価データ.xlsx")
