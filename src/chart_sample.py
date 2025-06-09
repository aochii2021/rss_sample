import win32com.client      #エクセル用
import mplfinance as mpf    #グラフ用
import pandas as pd         #データフレーム用
import time                 #時間調整用

#変数設定
code=7203       # 銘柄コード
bar="M"         # 足種
number=50      # 表示本数
row, column=1,1 # Rssの関数を入れる場所

#Rss関数で取り込んだエクセルデータをpandasのデータフレームへ変換する関数
def get_data(code, bar, number, row, column):
    #エクセルに入れる関数　RssChart(ヘッダー行,銘柄コード,足種,初期表示本数)
    command_line="=RssChart("+","+str(code)+","+"\""+bar+"\""+","+str(number)+")" 
    print("RSS関数:", command_line)  # デバッグ用に表示
    #Rss関数をエクセルに記入
    ws.Cells(row, column).Formula =command_line
    #エクセルに取り込んだデータを変数「data」に取り込む 
    data=ws.Range(ws.Cells(row+2,column+3), ws.Cells(row+number+1,column+9)).Value
    #データフレームに変換 columnsで各列に対応するタイトルを入れる。
    data=pd.DataFrame(data, columns=["date", "time", 'Open', 'High', 'Low', 'Close', 'Volume'])
    #日付と時間を合わせて、日時とする
    date_time =data["date"]+"/"+data["time"]
    #グラフの横軸に設定できるよう日時の文字をdatetime型へ変更する
    data["date"] = pd.to_datetime(date_time)
    #日時をインデックスとして、グラフの横軸にする
    data.set_index("date", inplace=True)
    return data

#今、開いているエクセルのシート「sheet1」をwsとする
try:
    wb = win32com.client.GetObject(Class="Excel.Application")   
except:
    print("エクセルが開いていません。")
    exit()
wb.Visible=True    
ws = wb.Worksheets('Sheet1')

#株価チャートの表示
while True:
    try:
        data=get_data(code, bar, number, row, column)
        print(data)  # デバッグ用に表示
        mpf.plot(data, type="candle",volume=True)
        print("株価チャートを表示しました。")
        break
    except:
        print("再試行中...")
        time.sleep(1)  # 待機する時間（秒）を指定する
