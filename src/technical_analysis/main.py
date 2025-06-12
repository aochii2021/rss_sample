import os
import sys
import pandas as pd
# import mplfinance as mpf
import matplotlib
matplotlib.rcParams['font.family'] = 'MS Gothic'  # または 'Meiryo' など
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
        def calc_group(group):
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


# ボリンジャーバンドを計算
def calculate_bollinger_bands(df: pd.DataFrame, price_col: str = '終値', window: int = 20, num_std_dev: int = 2) -> pd.DataFrame:
    """
    ボリンジャーバンドを計算する
    :param df: 入力データフレーム
    :param price_col: 価格のカラム名
    :param window: 移動平均の期間
    :param num_std_dev: 標準偏差の倍数
    :return: ボリンジャーバンドを含むデータフレーム
    """
    if price_col not in df.columns:
        raise ValueError(f"DataFrame must contain '{price_col}' column.")
    
    # 移動平均と標準偏差を計算
    df['移動平均'] = df[price_col].rolling(window=window).mean()
    df['標準偏差'] = df[price_col].rolling(window=window).std()
    
    # ボリンジャーバンドを計算
    df['上限'] = df['移動平均'] + (num_std_dev * df['標準偏差'])
    df['下限'] = df['移動平均'] - (num_std_dev * df['標準偏差'])
    
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
    stock_code = 7014  # 例として銘柄コード7014を使用
    bar = TickType.MIN5.value  # 5分足
    # ファイル検索（../get_rss_chart_data/output/stock_chart_DAY_7014_*.csv）
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
    macd_data = calculate_macd(df_stock_chart, price_col='終値', short_window=12, long_window=26, signal_window=9, group_by_date=True)
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

    # デッドクロスとゴールデンクロスの検出
    # MACDとシグナルラインの差分
    macd_data['diff'] = macd_data['MACD'] - macd_data['シグナルライン']

    # ゴールデンクロス（下から上に抜けた瞬間）
    macd_data['ゴールデンクロス'] = ((macd_data['diff'].shift(1) < 0) & (macd_data['diff'] > 0)).astype(int)
    # デッドクロス（上から下に抜けた瞬間）
    macd_data['デッドクロス'] = ((macd_data['diff'].shift(1) > 0) & (macd_data['diff'] < 0)).astype(int)

    print("デッドクロスとゴールデンクロスの検出:")
    print(macd_data[['デッドクロス', 'ゴールデンクロス']])

    # --- 価格とMACDを1つのウィンドウに上下分割で描画 ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

    # 上段: 価格チャート
    ax1.plot(df_stock_chart.index, df_stock_chart['終値'], label='終値', color='blue')
    # ゴールデンクロスとデッドクロスの点を価格チャート上に表示
    ax1.scatter(df_stock_chart.index[macd_data['ゴールデンクロス'] == 1], df_stock_chart['終値'][macd_data['ゴールデンクロス'] == 1], marker='o', color='green', label='Golden Cross')
    ax1.scatter(df_stock_chart.index[macd_data['デッドクロス'] == 1], df_stock_chart['終値'][macd_data['デッドクロス'] == 1], marker='x', color='black', label='Dead Cross')
    ax1.set_title(f'銘柄コード {stock_code} の {bar} チャート')
    ax1.set_ylabel('価格')
    ax1.legend()
    ax1.grid()

    # 下段: MACDとシグナルライン、クロス点
    ax2.plot(macd_data.index, macd_data['MACD'], label='MACD', color='blue')
    ax2.plot(macd_data.index, macd_data['シグナルライン'], label='Signal Line', color='red')
    ax2.scatter(macd_data.index[macd_data['デッドクロス'] == 1], macd_data['MACD'][macd_data['デッドクロス'] == 1], marker='x', color='black', label='Dead Cross')
    ax2.scatter(macd_data.index[macd_data['ゴールデンクロス'] == 1], macd_data['MACD'][macd_data['ゴールデンクロス'] == 1], marker='o', color='green', label='Golden Cross')
    ax2.set_title('MACD with Dead and Golden Crosses')
    ax2.set_xlabel('本数')
    ax2.set_ylabel('MACD')
    ax2.legend()
    ax2.grid()

    plt.tight_layout()
    plt.savefig('price_macd_crosses_plot.png')
    plt.show()

    # ボリンジャーバンドを計算
    bollinger_data = calculate_bollinger_bands(df_stock_chart)
    print("ボリンジャーバンド:")
    print(bollinger_data[['移動平均', '上限', '下限']])
    # ボリンジャーバンドのグラフを描画
    plt.figure(figsize=(12, 6))
    plt.plot(bollinger_data.index, bollinger_data['終値'], label='終値', color='blue')
    plt.plot(bollinger_data.index, bollinger_data['移動平均'], label='移動平均', color='orange')
    plt.fill_between(bollinger_data.index, bollinger_data['上限'], bollinger_data['下限'], color='lightgray', alpha=0.5, label='Bollinger Bands')
    plt.title('Bollinger Bands')
    plt.xlabel('本数')
    plt.ylabel('価格')
    plt.legend()
    plt.savefig('bollinger_bands_plot.png')
    plt.show()

    # --- 日別で売買シミュレーション ---
    if '日付' in df_stock_chart.columns:
        trade_results = []
        for date, group in macd_data.groupby('日付'):
            position = None
            buy_price = None
            trades = []
            for idx, row in group.iterrows():
                price = df_stock_chart.loc[idx, '終値'] if idx in df_stock_chart.index else None
                if row['ゴールデンクロス'] == 1 and position is None and price is not None:
                    position = 'buy'
                    buy_price = price
                    trades.append({'type': 'buy', 'date': idx, 'price': buy_price})
                elif row['デッドクロス'] == 1 and position == 'buy' and price is not None:
                    position = None
                    sell_price = price
                    trades.append({'type': 'sell', 'date': idx, 'price': sell_price})
                    trade_results.append({'date': date, 'buy': buy_price, 'sell': sell_price, 'profit': sell_price - buy_price})
                    buy_price = None
        # 日別損益のグラフ
        if trade_results:
            trade_df = pd.DataFrame(trade_results)
            trade_df['cum_profit'] = trade_df['profit'].cumsum()
            plt.figure(figsize=(12, 6))
            plt.plot(trade_df['date'], trade_df['cum_profit'], marker='o', label='Cumulative Profit')
            plt.title('日別MACDクロス売買シミュレーション累積損益')
            plt.xlabel('日付')
            plt.ylabel('累積損益')
            plt.legend()
            plt.grid()
            plt.savefig('macd_cross_trade_cum_profit.png')
            plt.show()
            print(trade_df[['date', 'buy', 'sell', 'profit', 'cum_profit']])
        else:
            print('売買シグナルがありませんでした。')

if __name__ == "__main__":
    main()