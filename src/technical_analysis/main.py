import os
import sys
import pandas as pd
# import mplfinance as mpf
from matplotlib import pyplot as plt
import glob

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common import common, columns
from common.data import StockCodeMaster
from common.rss import RssChart, DataRange, TickType
S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))


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
    
    # 価格帯の範囲を定義（例：10円刻み）
    price_bins = pd.cut(df[price_col], bins=range(0, int(df[price_col].max()) + 10, 10))

    # 価格帯ごとの出来高を集計
    volume_by_price = df.groupby(price_bins)[volume_col].sum().reset_index()
    
    return volume_by_price


# MACDを計算
def calculate_macd(df: pd.DataFrame, price_col: str = '終値', short_window: int = 12, long_window: int = 26, signal_window: int = 9) -> pd.DataFrame:
    """
    MACDを計算する
    :param df: 入力データフレーム
    :param price_col: 価格のカラム名
    :param short_window: 短期EMAの期間
    :param long_window: 長期EMAの期間
    :param signal_window: シグナルラインの期間
    :return: MACDとシグナルラインを含むデータフレーム
    """
    if price_col not in df.columns:
        raise ValueError(f"DataFrame must contain '{price_col}' column.")
    
    # 短期EMAと長期EMAを計算
    df['短期EMA'] = df[price_col].ewm(span=short_window, adjust=False).mean()
    df['長期EMA'] = df[price_col].ewm(span=long_window, adjust=False).mean()
    
    # MACDとシグナルラインを計算
    df['MACD'] = df['短期EMA'] - df['長期EMA']
    df['シグナルライン'] = df['MACD'].ewm(span=signal_window, adjust=False).mean()
    
    return df


def main():
    # 銘柄コードマスターの読み込み
    stock_code_master = StockCodeMaster()
    stock_code_master.load()
    
    # 銘柄コードの一覧を表示
    print("銘柄コード一覧:")
    print(stock_code_master.get_all_codes())
    
    # 全銘柄のデータを取得
    all_data = stock_code_master.get_all()
    print("全銘柄データ:")
    print(all_data)
    # データフレームのカラム名を表示
    print("データフレームのカラム名:")
    print(all_data.columns.tolist())
    # データフレームの先頭5行を表示
    print("データフレームの先頭5行:")
    print(all_data.head())

    # 銘柄の分足データを取得
    stock_code = 8136  # 例として銘柄コード8136を使用
    bar = TickType.DAY.value  # 日足
    # ファイル検索（../get_rss_chart_data/output/stock_chart_DAY_8136_*.csv）
    file_name = f'stock_chart_{bar}_{stock_code}_*.csv'
    S_RSS_CHART_DIR = os.path.dirname(S_FILE_DIR)
    file_list = glob.glob(os.path.join(S_RSS_CHART_DIR, 'get_rss_chart_data', 'output', file_name))
    if not file_list:
        print(f"銘柄コード {stock_code} のデータが見つかりません。")
        return

    # 最初のファイルを読み込む
    df_stock_chart = pd.read_csv(
        os.path.join(S_FILE_DIR, 'output', file_list[0]),
        encoding='utf-8-sig'
    )

    # チャートを描画
    df_stock_chart.sort_index(inplace=True)
    # データフレームのカラム名を表示
    print("チャートデータのカラム名:")
    print(df_stock_chart.columns.tolist())
    # データフレームの先頭5行を表示
    print("チャートデータの先頭5行:")
    print(df_stock_chart.head())
    # チャートの描画
    plt.figure(figsize=(12, 6))
    plt.plot(df_stock_chart.index, df_stock_chart['終値'], label='終値', color='blue')
    plt.title(f'銘柄コード {stock_code} の {bar} チャート')
    plt.xlabel('本数')
    plt.ylabel('価格')
    plt.legend()
    plt.grid()
    plt.savefig('stock_chart_plot.png')
    plt.show()

    # 価格帯別出来高を計算
    volume_by_price = calculate_volume_by_price(df_stock_chart)
    print("価格帯別出来高:")
    print(volume_by_price)
    # MACDを計算
    macd_data = calculate_macd(df_stock_chart)
    print("MACD:")
    print(macd_data[['MACD', 'シグナルライン']])
    # MACDのグラフを描画
    plt.figure(figsize=(12, 6))
    plt.plot(macd_data.index, macd_data['MACD'], label='MACD', color='blue')
    plt.plot(macd_data.index, macd_data['シグナルライン'], label='Signal Line', color='red')
    plt.title('MACD')
    plt.xlabel('本数')
    plt.ylabel('MACD')
    plt.legend()
    plt.savefig('macd_plot.png')
    plt.show()
if __name__ == "__main__":
    main()