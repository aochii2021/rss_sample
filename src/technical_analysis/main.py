import os
import sys
import pandas as pd
# import mplfinance as mpf
import matplotlib
matplotlib.rcParams['font.family'] = 'MS Gothic'  # または 'Meiryo' など
from matplotlib import pyplot as plt
import glob
import plotly.graph_objs as go
import plotly.offline as pyo
import plotly.subplots as psub

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
    # print(stock_code_master.get_all_codes())
    
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
    stock_code = 7011  # 例として銘柄コード7011を使用
    bar = TickType.MIN5.value  # 5分足
    # ファイル検索（../get_rss_chart_data/output/stock_chart_MIN5_7011_*.csv）
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

    # 日付が2025/06/09のデータをフィルタリング
    # if '日付' in df_stock_chart.columns:
    #     df_stock_chart = df_stock_chart[df_stock_chart['日付'] == '2025/06/09']

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
    group_by_date = True if bar != TickType.DAY.value and bar != TickType.WEEK.value and bar != TickType.MONTH.value else False
    macd_data = calculate_macd(df_stock_chart, price_col='終値', short_window=12, long_window=26, signal_window=9, group_by_date=group_by_date)
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

    # --- 売買シグナル判定・履歴・可視化を統合 ---
    trade_on_cross_only = False  # True:クロスのみ, False:ボリンジャー条件も考慮
    N = 5
    position = 0
    buy_points = []
    sell_points = []
    trade_results = []
    buy_price = None
    buy_time = None
    for i in range(len(macd_data)):
        # 日付・時刻取得
        date_str = df_stock_chart.iloc[i]['日付'] if '日付' in df_stock_chart.columns else ''
        time_str = df_stock_chart.iloc[i]['時刻'] if '時刻' in df_stock_chart.columns else ''
        price = df_stock_chart.iloc[i]['終値']
        bb_plus2 = bollinger_data.iloc[i]['上限'] if '上限' in bollinger_data.columns else None
        bb_plus1 = bollinger_data.iloc[i]['移動平均'] + bollinger_data.iloc[i]['標準偏差'] if '移動平均' in bollinger_data.columns and '標準偏差' in bollinger_data.columns else None
        if trade_on_cross_only:
            buy_cond = macd_data['ゴールデンクロス'].iloc[i] == 1
            sell_cond = macd_data['デッドクロス'].iloc[i] == 1
        else:
            buy_cond = (
                (macd_data['ゴールデンクロス'].iloc[max(0, i-N+1):i+1].any()) and
                (price > bb_plus2 if bb_plus2 is not None else False)
            )
            sell_cond = (
                (macd_data['デッドクロス'].iloc[max(0, i-N+1):i+1].any()) or
                (price < bb_plus1 if bb_plus1 is not None else False)
            )
        if position == 0 and buy_cond:
            position = 1
            buy_points.append(i)
            buy_price = price
            buy_time = time_str
        elif position == 1 and sell_cond:
            position = 0
            sell_points.append(i)
            sell_price = price
            sell_time = time_str
            trade_results.append({
                'date': date_str,
                'buy': buy_price,
                'buy_time': buy_time,
                'sell': sell_price,
                'sell_time': sell_time,
                'profit': sell_price - buy_price
            })
            buy_price = None
            buy_time = None
    # 損益累積和
    if trade_results:
        trade_df = pd.DataFrame(trade_results)
        trade_df['cum_profit'] = trade_df['profit'].cumsum()
        print(trade_df[['date', 'buy_time', 'buy', 'sell_time', 'sell', 'profit', 'cum_profit']])
        plt.figure(figsize=(12, 6))
        plt.plot(trade_df['date'] + ' ' + trade_df['buy_time'], trade_df['cum_profit'], marker='o', label='Cumulative Profit')
        plt.title('MACDクロス売買シミュレーション累積損益')
        plt.xlabel('日付・時刻')
        plt.ylabel('累積損益')
        plt.legend()
        plt.grid()
        plt.savefig('macd_cross_trade_cum_profit.png')
        plt.show()
    else:
        print('売買シグナルがありませんでした。')

    # --- Plotlyで価格・MACD・売買タイミングを可視化 ---
    # 日付・時刻列が存在する場合はhover用に使う
    if '日付' in df_stock_chart.columns and '時刻' in df_stock_chart.columns:
        hover_text = df_stock_chart['日付'].astype(str) + ' ' + df_stock_chart['時刻'].astype(str)
    elif '日付' in df_stock_chart.columns:
        hover_text = df_stock_chart['日付'].astype(str)
    elif '時刻' in df_stock_chart.columns:
        hover_text = df_stock_chart['時刻'].astype(str)
    else:
        hover_text = df_stock_chart.index.astype(str)

    # 価格チャート
    price_trace = go.Scatter(
        x=df_stock_chart.index,
        y=df_stock_chart['終値'],
        mode='lines',
        name='終値',
        text=hover_text,
        hovertemplate='日付: %{text}<br>価格: %{y}<extra></extra>'
    )
    # 売買タイミング
    buy_trace = go.Scatter(
        x=df_stock_chart.index[buy_points],
        y=df_stock_chart['終値'].iloc[buy_points],
        mode='markers',
        marker=dict(color='green', symbol='circle', size=10),
        name='Buy',
        text=hover_text.iloc[buy_points] if hasattr(hover_text, 'iloc') else None,
        hovertemplate='買い<br>日付・時間: %{text}<br>価格: %{y}<extra></extra>'
    )
    sell_trace = go.Scatter(
        x=df_stock_chart.index[sell_points],
        y=df_stock_chart['終値'].iloc[sell_points],
        mode='markers',
        marker=dict(color='red', symbol='x', size=10),
        name='Sell',
        text=hover_text.iloc[sell_points] if hasattr(hover_text, 'iloc') else None,
        hovertemplate='売り<br>日付・時間: %{text}<br>価格: %{y}<extra></extra>'
    )
    # MACD
    macd_trace = go.Scatter(
        x=macd_data.index,
        y=macd_data['MACD'],
        mode='lines',
        name='MACD',
        yaxis='y2',
        text=hover_text,
        hovertemplate='日付・時間: %{text}<br>MACD: %{y}<extra></extra>'
    )
    signal_trace = go.Scatter(
        x=macd_data.index,
        y=macd_data['シグナルライン'],
        mode='lines',
        name='Signal Line',
        yaxis='y2',
        text=hover_text,
        hovertemplate='日付・時間: %{text}<br>Signal: %{y}<extra></extra>'
    )
    # レイアウト
    layout = go.Layout(
        title=f'銘柄コード {stock_code} の {bar} チャートとMACD/売買タイミング',
        xaxis=dict(title='本数'),
        yaxis=dict(title='価格'),
        yaxis2=dict(title='MACD', overlaying='y', side='right', showgrid=False),
        legend=dict(x=0, y=1.1, orientation='h'),
        hovermode='x unified',
        height=800
    )
    fig = go.Figure(data=[price_trace, buy_trace, sell_trace, macd_trace, signal_trace], layout=layout)
    pyo.plot(fig, filename='price_macd_crosses_trade_points_plotly.html', auto_open=True)

if __name__ == "__main__":
    main()