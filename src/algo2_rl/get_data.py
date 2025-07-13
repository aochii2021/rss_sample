# src/main.py
import sys
import os
import win32com.client
import pandas as pd
from dataclasses import fields

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.rss import RssChart, RssMarket, MarketStatusItem, TickType, DataRange
from common.data import StockCodeMaster

S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
# 出力ディレクトリの設定
S_OUTPUT_DIR = os.path.join(S_FILE_DIR, 'output')


def get_rss_market(ws, stock_code: str, item_list: list[MarketStatusItem]) -> pd.DataFrame:
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


def get_stock_charts(ws, tick_type: TickType, number: int, stock_code: str) -> pd.DataFrame:
    bar = tick_type.value  # 足種
    header_row = 2
    # データクラスからカラム名を取得
    rss_chart_range = DataRange(start_row=3, start_col=4, end_row=number + 2, end_col=10)
    rss_chart = RssChart(ws, stock_code, bar, number, rss_chart_range, header_row)
    df = rss_chart.get_dataframe()

    # 型変換
    df["始値"] = pd.to_numeric(df["始値"], errors='coerce')
    df["高値"] = pd.to_numeric(df["高値"], errors='coerce')
    df["安値"] = pd.to_numeric(df["安値"], errors='coerce')
    df["終値"] = pd.to_numeric(df["終値"], errors='coerce')
    df["出来高"] = pd.to_numeric(df["出来高"], errors='coerce')
    print(f"df dtypes:\n{df.dtypes}")  # デバッグ用
    return df


# 価格帯別出来高を計算
def calculate_volume_by_price(df: pd.DataFrame, price_col: str = '終値', volume_col: str = '出来高') -> pd.DataFrame:
    """
    価格帯別出来高を計算する
    :param df: 入力データフレーム
    :param price_col: 価格のカラム名
    :param volume_col: 出来高のカラム名
    :return: 価格帯別出来高を含むデータフレーム
    """
    if price_col not in df.columns or volume_col not in df.columns:
        raise ValueError(f"DataFrame must contain '{price_col}' and '{volume_col}' columns.")
    
    # 価格帯の範囲を定義（例：5円刻み）
    price_bins = pd.cut(df[price_col], bins=range(0, int(df[price_col].max()) + 5, 5))

    # 価格帯ごとの出来高を集計
    volume_by_price = df.groupby(price_bins)[volume_col].sum().reset_index()
    
    return volume_by_price


# MACDを計算
def calculate_macd(df: pd.DataFrame, price_col: str = '終値', short_window: int = 12, long_window: int = 26, signal_window: int = 9, group_by_date: bool = False) -> pd.DataFrame:
    """
    MACDを計算する（日付ごとにグループ化も可能）
    :param df: 入力データフレーム
    :param price_col: 価格のカラム名
    :param short_window: 短期EMAの期間
    :param long_window: 長期EMAの期間
    :param signal_window: シグナルラインの期間
    :param group_by_date: Trueなら日付ごとにMACDを計算
    :return: MACDとシグナルラインを含むデータフレーム
    """
    if price_col not in df.columns:
        raise ValueError(f"DataFrame must contain '{price_col}' column.")
    result = df.copy()
    if group_by_date and '日付' in result.columns:
        def calc_group(group: pd.DataFrame) -> pd.DataFrame:
            group = group.copy()
            group['短期EMA'] = group[price_col].ewm(span=short_window, adjust=False).mean()
            group['長期EMA'] = group[price_col].ewm(span=long_window, adjust=False).mean()
            group['MACD'] = group['短期EMA'] - group['長期EMA']
            group['シグナルライン'] = group['MACD'].ewm(span=signal_window, adjust=False).mean()
            return group
        result = result.groupby('日付', group_keys=False).apply(calc_group)
    else:
        result['短期EMA'] = result[price_col].ewm(span=short_window, adjust=False).mean()
        result['長期EMA'] = result[price_col].ewm(span=long_window, adjust=False).mean()
        result['MACD'] = result['短期EMA'] - result['長期EMA']
        result['シグナルライン'] = result['MACD'].ewm(span=signal_window, adjust=False).mean()
    return result


def main():
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")  # 今、開いている空白のブック
    except Exception as e:
        print("エクセルが開いていません。", e)
        return

    xl.Visible = True
    ws = xl.Worksheets('Sheet1')

    # 銘柄コードを指定
    stock_code = "6758" # 例としてソニーグループの銘柄コードを指定

    # RSSマーケットデータの取得
    market_status_item_list = [  # 取得したいマーケットステータスの項目
        MarketStatusItem.STOCK_CODE,
        MarketStatusItem.CURRENT_PRICE,
        MarketStatusItem.PREV_DAY_DIFF,
        MarketStatusItem.PER,
        MarketStatusItem.PBR,
        MarketStatusItem.VOLUME,
    ]
    df_market = get_rss_market(ws, stock_code, market_status_item_list)
    output_file = os.path.join(S_OUTPUT_DIR, 'rss_market_data.csv')
    df_market.to_csv(output_file, index=False)
    print(f"Saved rss_market_data: {output_file}")

    # RSSチャートデータの取得
    tick_type = TickType.MIN5  # 5分足データを取得
    number = 3000  # 取得するデータ数
    df_chart = get_stock_charts(ws, tick_type, number, stock_code)
    start_date = df_chart['日付'].dropna().min()  # 最初の日付
    end_date = df_chart['日付'].dropna().max()  # 最後の日付
    # スラッシュを削除
    start_date = start_date.replace("/", "")
    end_date = end_date.replace("/", "")
    print(f"取得したデータの期間: {start_date} から {end_date}")
    output_file = os.path.join(S_OUTPUT_DIR, f'stock_chart_{tick_type.value}_{stock_code}_{start_date}_{end_date}.csv')
    df_chart.to_csv(output_file, index=False)
    print(f"Saved stock chart data: {output_file}")

    # 価格帯別出来高の計算
    df_volume_by_price = calculate_volume_by_price(df_chart)
    output_file = os.path.join(S_OUTPUT_DIR, f'volume_by_price_{stock_code}_{start_date}_{end_date}.csv')
    df_volume_by_price.to_csv(output_file, index=False)
    print(f"Saved volume by price data: {output_file}")

    # MACDの計算
    df_macd = calculate_macd(df_chart, group_by_date=True)
    output_file = os.path.join(S_OUTPUT_DIR, f'macd_{stock_code}_{start_date}_{end_date}.csv')
    df_macd.to_csv(output_file, index=False)


if __name__ == "__main__":
    main()