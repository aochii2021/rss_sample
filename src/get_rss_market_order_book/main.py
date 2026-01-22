# src/main.py
import sys
import os
import win32com.client
import pandas as pd
from dataclasses import fields
import schedule
import time
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.rss import RssMarket, MarketStatusItem, DataRange
from common.data import StockCodeMaster
from common import common, columns

S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
# 出力ディレクトリの設定
S_OUTPUT_DIR = os.path.join(S_FILE_DIR, 'output')
WATCHLIST_FILE = os.path.join(S_FILE_DIR, 'input', 'watchlist.csv')

# グローバル変数として実行セッションのディレクトリを保持
SESSION_DIR = None


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


def load_watchlist() -> list[str]:
    """
    CSVファイルから監視銘柄コードを読み込む
    :return: 銘柄コードのリスト
    """
    if not os.path.exists(WATCHLIST_FILE):
        print(f"監視銘柄リストファイルが見つかりません: {WATCHLIST_FILE}")
        return []

    df = pd.read_csv(WATCHLIST_FILE)
    if 'コード' in df.columns:
        return df['コード'].astype(str).tolist()
    else:
        print("CSVファイルに'コード'列が存在しません。")
        return []


def record_market_data():
    global SESSION_DIR
    
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")
    except Exception as e:
        print(f"エラー: エクセルが開いていません。 {e}")
        return

    try:
        xl.Visible = True
        # ワークシートを毎回取得し直す
        ws = xl.Worksheets('Sheet1')
        
        # シート全体をクリアして初期化
        ws.Cells.ClearContents()

        market_status_item_list = [
            item for item in MarketStatusItem  # 全てのマーケットステータス項目を取得
        ]

        stock_code_list = load_watchlist()
        if not stock_code_list:
            print("監視銘柄がありません。")
            return

        current_time = datetime.now()
        print(f"\n[{current_time.strftime('%H:%M:%S')}] データ取得開始...")

        # 監視銘柄のみのマーケットデータを取得
        df = get_all_rss_market(ws, stock_code_list, market_status_item_list)
        
        # タイムスタンプを追加
        df.insert(0, '記録日時', current_time.strftime('%Y-%m-%d %H:%M:%S'))
        
        output_file = os.path.join(SESSION_DIR, 'rss_market_data.csv')

        # CSVに追記
        if not os.path.exists(output_file):
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
        else:
            df.to_csv(output_file, mode='a', header=False, index=False, encoding='utf-8-sig')

        print(f"[{current_time.strftime('%H:%M:%S')}] データをCSVファイルに追記しました ✓")
        
    except Exception as e:
        current_time = datetime.now()
        print(f"[{current_time.strftime('%H:%M:%S')}] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        print("次の記録タイミングで再試行します...")


def create_session_info(session_dir: str, stock_code_list: list[str], start_time: datetime):
    """
    実行条件をまとめたファイルを作成
    """
    # 実行条件をテキストファイルに保存
    info_file = os.path.join(session_dir, 'session_info.txt')
    with open(info_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("板情報記録セッション情報\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"記録開始時刻: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"監視銘柄数: {len(stock_code_list)}\n\n")
        f.write("監視銘柄一覧:\n")
        for code in stock_code_list:
            f.write(f"  - {code}\n")
        f.write("\n")
        f.write("記録間隔: 1分\n")
        f.write("出力ファイル: rss_market_data.csv\n")
    
    # 監視銘柄リストをCSVとしてコピー
    import shutil
    watchlist_copy = os.path.join(session_dir, 'watchlist.csv')
    shutil.copy(WATCHLIST_FILE, watchlist_copy)
    
    print(f"セッション情報ファイルを作成しました: {info_file}")


def main():
    global SESSION_DIR
    
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")  # 今、開いている空白のブック
    except Exception as e:
        print("エクセルが開いていません。", e)
        return

    xl.Visible = True
    ws = xl.Worksheets('Sheet1')

    market_status_item_list = [
        item for item in MarketStatusItem  # 全てのマーケットステータス項目を取得
    ]

    # 銘柄コードマスターの読み込み
    stock_code_list = load_watchlist()
    if not stock_code_list:
        print("監視銘柄がありません。")
        return
    
    # 実行開始時刻
    start_time = datetime.now()
    
    # セッションディレクトリを作成 (YYYYMMDD_HHMM形式)
    session_name = start_time.strftime('%Y%m%d_%H%M')
    SESSION_DIR = os.path.join(S_OUTPUT_DIR, session_name)
    os.makedirs(SESSION_DIR, exist_ok=True)
    
    print("\n" + "=" * 60)
    print(f"板情報記録セッション: {session_name}")
    print("=" * 60)
    print(f"記録開始時刻: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"出力ディレクトリ: {SESSION_DIR}")
    print(f"監視銘柄数: {len(stock_code_list)}")
    print("\n監視銘柄コード一覧:")
    for code in stock_code_list:
        print(f"  - {code}")
    print()
    
    # セッション情報ファイルを作成
    create_session_info(SESSION_DIR, stock_code_list, start_time)
    
    # 初回データ取得
    df = get_all_rss_market(ws, stock_code_list, market_status_item_list)
    print("初回データ取得完了:")
    print(df.head())  # 最初の5行を表示
    
    # タイムスタンプを追加
    df.insert(0, '記録日時', start_time.strftime('%Y-%m-%d %H:%M:%S'))
    
    # save DataFrame to csv file
    output_file = os.path.join(SESSION_DIR, 'rss_market_data.csv')
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"データをCSVファイルに保存しました: {output_file}")

    schedule.every(1).minutes.do(record_market_data)

    print("\n" + "=" * 60)
    print("1分おきに板情報を記録します...")
    print("停止する場合は Ctrl+C を押してください")
    print("=" * 60 + "\n")
    
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()