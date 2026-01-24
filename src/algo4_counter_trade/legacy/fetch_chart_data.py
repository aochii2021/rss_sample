#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
指定銘柄の日足・3分足データをRSS APIで取得
"""
import sys
import os
import win32com.client
import pandas as pd
import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.rss import RssChart, DataRange, TickType

# 対象銘柄リスト
TARGET_SYMBOLS = ['3350', '9501', '9509', '215A', '6315', '6526', '5016']

# 出力ディレクトリ
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'input', 'chart_data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_chart_for_symbol(ws, symbol: str, tick_type: TickType, bars: int):
    """指定銘柄・足種でチャートデータ取得"""
    bar = tick_type.value
    header_row = 2
    date_col = "日付"
    
    print(f"Fetching {symbol} {bar} {bars}本...")
    
    try:
        rss_chart_range = DataRange(start_row=3, start_col=4, end_row=bars + 2, end_col=10)
        rss_chart = RssChart(ws, symbol, bar, bars, rss_chart_range, header_row)
        df = rss_chart.get_dataframe()
        
        if df.empty:
            print(f"  WARNING: No data for {symbol} {bar}")
            return
        
        # 日付範囲取得
        if date_col in df.columns:
            start_date = df[date_col].iloc[0].replace('/', '') if not df.empty else None
            end_date = df[date_col].iloc[-1].replace('/', '') if not df.empty else None
        else:
            start_date = end_date = None
        
        df["symbol"] = symbol
        
        # CSVファイル名
        csv_file = os.path.join(OUTPUT_DIR, f"{symbol}_{bar}_{bars}bars_{start_date}_{end_date}.csv")
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"  Saved: {csv_file} ({len(df)} rows)")
    except Exception as e:
        print(f"  ERROR: {symbol} {bar}取得失敗: {e}")
        import traceback
        traceback.print_exc()

def main():
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")
    except Exception as e:
        print("ERROR: Excelが開いていません。", e)
        return
    
    xl.Visible = True
    
    # Sheet1が存在しない場合は作成
    try:
        ws = xl.Worksheets('Sheet1')
    except:
        ws = xl.Worksheets.Add()
        ws.Name = 'Sheet1'
    
    exec_date = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    print(f"=== Chart Data Fetch ({exec_date}) ===")
    print(f"対象銘柄: {TARGET_SYMBOLS}")
    print()
    
    # 日足3000本取得
    print("【日足 3000本】")
    for symbol in TARGET_SYMBOLS:
        fetch_chart_for_symbol(ws, symbol, TickType.DAY, 3000)
    
    print()
    
    # 3分足3000本取得
    print("【3分足 3000本】")
    for symbol in TARGET_SYMBOLS:
        fetch_chart_for_symbol(ws, symbol, TickType.MIN3, 3000)
    
    print()
    print("=== 完了 ===")

if __name__ == "__main__":
    main()
