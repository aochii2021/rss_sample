import sys
import os
import pandas as pd
import datetime
import glob
from typing import List, Tuple
from tqdm import tqdm

# 親ディレクトリのパスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.data import StockCodeMaster
from common import common, columns

S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
S_INPUT_DIR = os.path.join(S_FILE_DIR, 'input')
S_OUTPUT_DIR = os.path.join(S_FILE_DIR, 'output')

class BreakNewHighAnalyzer:
    """新高値ブレイク投資法の分析クラス"""
    
    def __init__(self):
        self.stock_code_master = StockCodeMaster()
        self.stock_code_master.load()
    
    def load_stock_data_from_folder(self, folder_path: str) -> pd.DataFrame:
        """
        指定フォルダから全銘柄のCSVデータを読み込み、統合したDataFrameを作成
        
        Args:
            folder_path: CSVファイルが格納されているフォルダパス
            
        Returns:
            統合されたDataFrame
        """
        all_data = []
        csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
        
        # プログレスバーで読み込み進行状況を表示
        with tqdm(total=len(csv_files), desc="📁 CSVファイル読み込み", unit="file") as pbar:
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file, encoding='utf-8-sig')
                    if not df.empty:
                        # ファイル名から銘柄コードを抽出（例: stock_chart_W_130A_20240719_20250711.csv）
                        filename = os.path.basename(csv_file)
                        if '銘柄コード' not in df.columns:
                            # ファイル名から銘柄コードを抽出
                            parts = filename.split('_')
                            if len(parts) >= 3:
                                stock_code = parts[2]
                                df['銘柄コード'] = stock_code
                        
                        all_data.append(df)
                    pbar.set_postfix({"ファイル": os.path.basename(csv_file)})
                except Exception as e:
                    tqdm.write(f"❌ ファイル読み込みエラー: {csv_file}, エラー: {e}")
                pbar.update(1)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            # 銘柄コードを文字列型に統一
            combined_df['銘柄コード'] = combined_df['銘柄コード'].astype(str)
            tqdm.write(f"✅ 統合完了: {len(combined_df):,}件のデータ, {combined_df['銘柄コード'].nunique()}銘柄")
            return combined_df
        else:
            tqdm.write("⚠️ 読み込めるデータがありませんでした。")
            return pd.DataFrame()
    
    def find_new_highs(self, df: pd.DataFrame, period_weeks: int = 52) -> pd.DataFrame:
        """
        新高値を付けた銘柄を選出
        
        Args:
            df: 株価データのDataFrame
            period_weeks: 高値更新期間（週数）
            
        Returns:
            新高値銘柄のDataFrame
        """
        new_high_stocks = []
        stock_codes = df['銘柄コード'].unique()
        
        # 銘柄コードごとに分析
        with tqdm(total=len(stock_codes), desc="🔍 新高値銘柄検索", unit="銘柄") as pbar:
            for stock_code in stock_codes:
                stock_df = df[df['銘柄コード'] == stock_code].copy()
                
                if len(stock_df) == 0:
                    pbar.update(1)
                    continue
                
                # 日付でソート
                stock_df['日付'] = pd.to_datetime(stock_df['日付'])
                stock_df = stock_df.sort_values('日付').reset_index(drop=True)
                
                # 最新の高値を取得
                latest_high = stock_df['高値'].iloc[-1]
                latest_date = stock_df['日付'].iloc[-1]
                
                # 過去の最高値を計算（最新データを除く）
                if len(stock_df) > 1:
                    historical_data = stock_df.iloc[:-1]
                    historical_max = historical_data['高値'].max()
                    
                    # 新高値判定
                    if latest_high > historical_max:
                        # 銘柄情報を取得 - 銘柄コードの型を確実に文字列にする
                        stock_code_str = str(stock_code).strip()
                        stock_info = self.stock_code_master.get_by_code(stock_code_str)
                        stock_name = stock_info['name'].iloc[0] if not stock_info.empty else "不明"
                        
                        new_high_stocks.append({
                            '銘柄コード': stock_code_str,
                            '銘柄名': stock_name,
                            '新高値': latest_high,
                            '新高値日付': latest_date,
                            '過去最高値': historical_max,
                            '高値更新率': ((latest_high - historical_max) / historical_max * 100),
                            '分析期間_週': period_weeks,
                            '最新終値': stock_df['終値'].iloc[-1],
                            '最新出来高': stock_df['出来高'].iloc[-1]
                        })
                
                pbar.update(1)
        
        result_df = pd.DataFrame(new_high_stocks)
        
        if not result_df.empty:
            # 高値更新率でソート（降順）
            result_df = result_df.sort_values('高値更新率', ascending=False).reset_index(drop=True)
            tqdm.write(f"🎉 新高値銘柄数: {len(result_df)}銘柄")
        else:
            tqdm.write("📉 新高値を付けた銘柄はありませんでした。")
        
        return result_df
    
    def find_near_new_highs(self, df: pd.DataFrame, threshold_percent: float = 5.0) -> pd.DataFrame:
        """
        新高値を更新しそうな株を選出（過去高値の-X%以内）
        
        Args:
            df: 株価データのDataFrame
            threshold_percent: 過去高値からの乖離閾値（%）
            
        Returns:
            新高値更新候補銘柄のDataFrame
        """
        near_high_stocks = []
        stock_codes = df['銘柄コード'].unique()
        
        # 銘柄コードごとに分析
        with tqdm(total=len(stock_codes), desc="🔍 候補銘柄検索", unit="銘柄") as pbar:
            for stock_code in stock_codes:
                stock_df = df[df['銘柄コード'] == stock_code].copy()
                
                if len(stock_df) == 0:
                    pbar.update(1)
                    continue
                
                # 日付でソート
                stock_df['日付'] = pd.to_datetime(stock_df['日付'])
                stock_df = stock_df.sort_values('日付').reset_index(drop=True)
                
                # 最新の終値を取得
                latest_close = stock_df['終値'].iloc[-1]
                latest_date = stock_df['日付'].iloc[-1]
                
                # 過去の最高値を計算
                historical_max = stock_df['高値'].max()
                
                # 新高値更新候補の閾値を計算
                threshold_price = historical_max * (1 - threshold_percent / 100)
                
                # 高値までの乖離率を計算
                divergence_rate = ((historical_max - latest_close) / historical_max * 100)
                
                # 新高値更新候補判定
                if latest_close >= threshold_price and latest_close < historical_max:
                    # 銘柄情報を取得 - 銘柄コードの型を確実に文字列にする
                    stock_code_str = str(stock_code).strip()
                    stock_info = self.stock_code_master.get_by_code(stock_code_str)
                    stock_name = stock_info['name'].iloc[0] if not stock_info.empty else "不明"
                    
                    near_high_stocks.append({
                        '銘柄コード': stock_code_str,
                        '銘柄名': stock_name,
                        '最新終値': latest_close,
                        '最新日付': latest_date,
                        '過去最高値': historical_max,
                        '高値までの乖離率': divergence_rate,
                        '閾値価格': threshold_price,
                        '閾値_パーセント': threshold_percent,
                        '最新出来高': stock_df['出来高'].iloc[-1]
                    })
                
                pbar.update(1)
        
        result_df = pd.DataFrame(near_high_stocks)
        
        if not result_df.empty:
            # 高値までの乖離率でソート（昇順）
            result_df = result_df.sort_values('高値までの乖離率', ascending=True).reset_index(drop=True)
            tqdm.write(f"🎯 新高値候補銘柄数: {len(result_df)}銘柄")
        else:
            tqdm.write("📉 新高値更新候補銘柄はありませんでした。")
        
        return result_df
    
    def save_results(self, df: pd.DataFrame, filename: str, analysis_type: str):
        """
        分析結果をCSVファイルに保存
        
        Args:
            df: 保存するDataFrame
            filename: ファイル名
            analysis_type: 分析種別
        """
        # 実行日付を取得
        exec_date = datetime.datetime.now().strftime('%Y%m%d')
        
        # 出力ディレクトリを作成
        output_folder = os.path.join(S_OUTPUT_DIR, f"{exec_date}_{analysis_type}")
        os.makedirs(output_folder, exist_ok=True)
        
        # CSVファイルを保存
        output_path = os.path.join(output_folder, filename)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        tqdm.write(f"💾 結果保存: {filename} ({len(df)}件)")
        
        return output_path

def analyze_folder_data(folder_name: str):
    """
    指定フォルダのデータを分析する
    
    Args:
        folder_name: 分析対象フォルダ名（例: W_52_20250713）
    """
    analyzer = BreakNewHighAnalyzer()
    
    # フォルダパスを構築
    folder_path = os.path.join(S_INPUT_DIR, folder_name)
    
    if not os.path.exists(folder_path):
        tqdm.write(f"❌ フォルダが存在しません: {folder_path}")
        return
    
    tqdm.write(f"🚀 分析開始: {folder_name}")
    
    # データを読み込み
    df = analyzer.load_stock_data_from_folder(folder_path)
    
    if df.empty:
        tqdm.write("⚠️ 分析対象データがありません。")
        return
    
    # フォルダ名から期間を抽出（例: W_52_20250713 -> 52週）
    parts = folder_name.split('_')
    if len(parts) >= 2:
        try:
            period_weeks = int(parts[1])
        except ValueError:
            period_weeks = 52  # デフォルト値
    else:
        period_weeks = 52
    
    analysis_type = f"{period_weeks}week"
    
    # 1. 新高値銘柄の選出
    new_highs_df = analyzer.find_new_highs(df, period_weeks)
    if not new_highs_df.empty:
        analyzer.save_results(
            new_highs_df, 
            f"new_highs_{period_weeks}week.csv", 
            analysis_type
        )
        tqdm.write("\n=== 🏆 新高値銘柄トップ10 ===")
        print(new_highs_df[['銘柄コード', '銘柄名', '新高値', '高値更新率']].head(10))
    
    # 2. 新高値更新候補銘柄の選出
    near_highs_df = analyzer.find_near_new_highs(df, threshold_percent=5.0)
    if not near_highs_df.empty:
        analyzer.save_results(
            near_highs_df, 
            f"near_new_highs_{period_weeks}week.csv", 
            analysis_type
        )
        tqdm.write("\n=== 🎯 新高値更新候補銘柄トップ10 ===")
        print(near_highs_df[['銘柄コード', '銘柄名', '最新終値', '高値までの乖離率']].head(10))
    
    tqdm.write(f"\n✅ 分析完了: {folder_name}")

def main():
    """メイン処理"""
    print("=== 📈 新高値ブレイク投資法 分析開始 ===")
    
    # inputフォルダ内の全フォルダを取得
    if not os.path.exists(S_INPUT_DIR):
        print(f"❌ inputディレクトリが存在しません: {S_INPUT_DIR}")
        return
    
    # inputフォルダ内のサブフォルダを検索
    folders = [f for f in os.listdir(S_INPUT_DIR) if os.path.isdir(os.path.join(S_INPUT_DIR, f))]
    
    if not folders:
        print("⚠️ 分析対象フォルダがありません。")
        return
    
    print(f"📂 分析対象フォルダ: {folders}")
    
    # 各フォルダを分析
    for folder_name in folders:
        try:
            analyze_folder_data(folder_name)
        except Exception as e:
            print(f"❌ フォルダ {folder_name} の分析でエラーが発生しました: {e}")
    
    print("\n=== 🎉 分析終了 ===")

if __name__ == "__main__":
    main()