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
from common.rss import TickType
from common import common, columns

S_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
S_INPUT_DIR = os.path.join(S_FILE_DIR, 'input')
S_OUTPUT_DIR = os.path.join(S_FILE_DIR, 'output')

class BreakNewHighAnalyzer:
    """新高値ブレイク投資法の分析クラス"""
    
    def __init__(self):
        self.stock_code_master = StockCodeMaster()
        self.stock_code_master.load()
        self.market_data = None
        self._load_market_data()
    
    def _load_market_data(self):
        """
        市場データを読み込み
        """
        market_data_path = os.path.join(S_INPUT_DIR, 'market_data', 'rss_market_data.csv')
        if os.path.exists(market_data_path):
            try:
                with tqdm(desc="📊 市場データ読み込み", unit="件", leave=False) as pbar:
                    self.market_data = pd.read_csv(market_data_path, encoding='utf-8-sig')
                    pbar.total = len(self.market_data)
                    pbar.update(len(self.market_data))
                    
                    # 銘柄コードを文字列型に統一（小数点を削除）
                    if '銘柄コード' in self.market_data.columns:
                        self.market_data['銘柄コード'] = self.market_data['銘柄コード'].astype(str).str.replace('.0', '', regex=False)
                    
                    tqdm.write(f"✅ 市場データ読み込み完了: {len(self.market_data)}件")
            except Exception as e:
                tqdm.write(f"⚠️ 市場データ読み込みエラー: {e}")
                self.market_data = None
        else:
            tqdm.write(f"⚠️ 市場データファイルが見つかりません: {market_data_path}")
            self.market_data = None
    
    def get_stock_info(self, stock_code: str) -> dict:
        """
        銘柄情報を取得（銘柄マスターと市場データから）
        
        Args:
            stock_code: 銘柄コード
            
        Returns:
            銘柄情報の辞書
        """
        stock_code_str = str(stock_code).strip()
        
        # 銘柄マスターから銘柄名を取得
        stock_info = self.stock_code_master.get_by_code(stock_code_str)
        stock_name = stock_info['name'].iloc[0] if not stock_info.empty else "不明"
        
        # 結果の初期化
        result = {'銘柄名': stock_name}
        
        # 市場データから詳細情報を取得（pandasのmergeを使用）
        if self.market_data is not None:
            # 一時的なDataFrameを作成してmerge
            temp_df = pd.DataFrame({'銘柄コード': [stock_code_str]})
            merged_data = temp_df.merge(
                self.market_data, 
                on='銘柄コード', 
                how='left'
            )
            
            if not merged_data.empty and not merged_data.iloc[0].isna().all():
                # 市場データから取得する重要な指標を拡充
                market_columns = [
                    # 基本情報
                    '銘柄名称', '市場名称', '市場部名称', '市場部略称',
                    # 価格情報
                    '現在値', '前日比', '前日比率', '前日終値', '始値', '高値', '安値',
                    # 取引情報
                    '出来高', '売買代金', '出来高加重平均', '時価総額',
                    # 財務指標
                    'PER', 'PBR', '配当',
                    # 価格レンジ
                    '年初来高値', '年初来安値', '年初来高値日付', '年初来安値日付',
                    '上場来高値', '上場来安値', '上場来高値日付', '上場来安値日付',
                    # 信用取引情報
                    '信用倍率', '逆日歩', '信用売残', '信用買残', '信用売残前週比', '信用買残前週比',
                    '貸借倍率', '回転日数',
                    # その他指標
                    '単位株数', '配当落日', '決算発表日', '貸株金利',
                    # 気配情報
                    '最良売気配値', '最良買気配値'
                ]
                
                for col in market_columns:
                    if col in merged_data.columns:
                        value = merged_data[col].iloc[0]
                        # NaN、空文字列、0.0でない場合のみ追加
                        if pd.notna(value) and value != '' and value != 0.0:
                            result[col] = value
                
                # 銘柄名称が市場データにある場合は優先
                if '銘柄名称' in result:
                    result['銘柄名'] = result['銘柄名称']
        
        return result
    
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
        
        # 市場データファイルを除外
        csv_files = [f for f in csv_files if 'rss_market_data.csv' not in f]
        
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
                        
                        # 必要な列があるかチェック（株価データとして有効か）
                        required_columns = ['日付', '高値', '終値', '出来高']
                        if all(col in df.columns for col in required_columns):
                            all_data.append(df)
                        else:
                            tqdm.write(f"⚠️ 必要な列が不足しているファイルをスキップ: {filename}")
                            
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
                try:
                    stock_df['日付'] = pd.to_datetime(stock_df['日付'])
                    stock_df = stock_df.sort_values('日付').reset_index(drop=True)
                except Exception as e:
                    tqdm.write(f"⚠️ 銘柄 {stock_code} の日付変換エラー: {e}")
                    pbar.update(1)
                    continue
                
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
                        stock_info = self.get_stock_info(stock_code_str)
                        
                        new_high_stocks.append({
                            '銘柄コード': stock_code_str,
                            '銘柄名': stock_info['銘柄名'],
                            '新高値': latest_high,
                            '新高値日付': latest_date,
                            '過去最高値': historical_max,
                            '高値更新率': ((latest_high - historical_max) / historical_max * 100),
                            '分析期間_週': period_weeks,
                            '最新終値': stock_df['終値'].iloc[-1],
                            '最新出来高': stock_df['出来高'].iloc[-1],
                            # 市場データから取得した情報を追加
                            '市場名称': stock_info.get('市場名称'),
                            '市場部名称': stock_info.get('市場部名称'),
                            '現在値': stock_info.get('現在値'),
                            '前日比': stock_info.get('前日比'),
                            '前日比率': stock_info.get('前日比率'),
                            'PER': stock_info.get('PER'),
                            'PBR': stock_info.get('PBR'),
                            '配当': stock_info.get('配当'),
                            '時価総額': stock_info.get('時価総額'),
                            '売買代金': stock_info.get('売買代金'),
                            '年初来高値': stock_info.get('年初来高値'),
                            '年初来安値': stock_info.get('年初来安値'),
                            '年初来高値日付': stock_info.get('年初来高値日付'),
                            '年初来安値日付': stock_info.get('年初来安値日付'),
                            '上場来高値': stock_info.get('上場来高値'),
                            '上場来安値': stock_info.get('上場来安値'),
                            '信用倍率': stock_info.get('信用倍率'),
                            '信用売残': stock_info.get('信用売残'),
                            '信用買残': stock_info.get('信用買残'),
                            '貸借倍率': stock_info.get('貸借倍率'),
                            '回転日数': stock_info.get('回転日数'),
                            '単位株数': stock_info.get('単位株数'),
                            '決算発表日': stock_info.get('決算発表日'),
                            '貸株金利': stock_info.get('貸株金利')
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
                try:
                    stock_df['日付'] = pd.to_datetime(stock_df['日付'])
                    stock_df = stock_df.sort_values('日付').reset_index(drop=True)
                except Exception as e:
                    tqdm.write(f"⚠️ 銘柄 {stock_code} の日付変換エラー: {e}")
                    pbar.update(1)
                    continue
                
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
                    stock_info = self.get_stock_info(stock_code_str)
                    
                    near_high_stocks.append({
                        '銘柄コード': stock_code_str,
                        '銘柄名': stock_info['銘柄名'],
                        '最新終値': latest_close,
                        '最新日付': latest_date,
                        '過去最高値': historical_max,
                        '高値までの乖離率': divergence_rate,
                        '閾値価格': threshold_price,
                        '閾値_パーセント': threshold_percent,
                        '最新出来高': stock_df['出来高'].iloc[-1],
                        # 市場データから取得した情報を追加
                        '市場名称': stock_info.get('市場名称'),
                        '市場部名称': stock_info.get('市場部名称'),
                        '現在値': stock_info.get('現在値'),
                        '前日比': stock_info.get('前日比'),
                        '前日比率': stock_info.get('前日比率'),
                        'PER': stock_info.get('PER'),
                        'PBR': stock_info.get('PBR'),
                        '配当': stock_info.get('配当'),
                        '時価総額': stock_info.get('時価総額'),
                        '売買代金': stock_info.get('売買代金'),
                        '年初来高値': stock_info.get('年初来高値'),
                        '年初来安値': stock_info.get('年初来安値'),
                        '年初来高値日付': stock_info.get('年初来高値日付'),
                        '年初来安値日付': stock_info.get('年初来安値日付'),
                        '上場来高値': stock_info.get('上場来高値'),
                        '上場来安値': stock_info.get('上場来安値'),
                        '信用倍率': stock_info.get('信用倍率'),
                        '信用売残': stock_info.get('信用売残'),
                        '信用買残': stock_info.get('信用買残'),
                        '貸借倍率': stock_info.get('貸借倍率'),
                        '回転日数': stock_info.get('回転日数'),
                        '単位株数': stock_info.get('単位株数'),
                        '決算発表日': stock_info.get('決算発表日'),
                        '貸株金利': stock_info.get('貸株金利')
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
    # プログレスバーで分析全体の進行状況を表示
    with tqdm(total=4, desc=f"📊 {folder_name} 分析", unit="step") as main_pbar:
        analyzer = BreakNewHighAnalyzer()
        main_pbar.set_postfix({"ステップ": "初期化"})
        main_pbar.update(1)
        
        # フォルダパスを構築
        folder_path = os.path.join(S_INPUT_DIR, folder_name)
        
        if not os.path.exists(folder_path):
            tqdm.write(f"❌ フォルダが存在しません: {folder_path}")
            return
        
        # データを読み込み
        main_pbar.set_postfix({"ステップ": "データ読み込み"})
        df = analyzer.load_stock_data_from_folder(folder_path)
        main_pbar.update(1)
        
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
        main_pbar.set_postfix({"ステップ": "新高値銘柄選出"})
        new_highs_df = analyzer.find_new_highs(df, period_weeks)
        if not new_highs_df.empty:
            analyzer.save_results(
                new_highs_df, 
                f"new_highs_{period_weeks}week.csv", 
                analysis_type
            )
        main_pbar.update(1)
        
        # 2. 新高値更新候補銘柄の選出
        main_pbar.set_postfix({"ステップ": "候補銘柄選出"})
        near_highs_df = analyzer.find_near_new_highs(df, threshold_percent=5.0)
        if not near_highs_df.empty:
            analyzer.save_results(
                near_highs_df, 
                f"near_new_highs_{period_weeks}week.csv", 
                analysis_type
            )
        main_pbar.update(1)
        
        # 結果サマリーを表示
        tqdm.write(f"\n=== 📊 {folder_name} 分析結果サマリー ===")
        if not new_highs_df.empty:
            tqdm.write(f"🏆 新高値銘柄数: {len(new_highs_df)}銘柄")
            tqdm.write("=== 新高値銘柄トップ10 ===")
            top_new_highs = new_highs_df[['銘柄コード', '銘柄名', '新高値', '高値更新率']].head(10)
            for _, row in top_new_highs.iterrows():
                tqdm.write(f"  {row['銘柄コード']}: {row['銘柄名']} - 新高値:{row['新高値']:.0f} (+{row['高値更新率']:.2f}%)")
        
        if not near_highs_df.empty:
            tqdm.write(f"🎯 新高値候補銘柄数: {len(near_highs_df)}銘柄")
            tqdm.write("=== 新高値更新候補銘柄トップ10 ===")
            top_near_highs = near_highs_df[['銘柄コード', '銘柄名', '最新終値', '高値までの乖離率']].head(10)
            for _, row in top_near_highs.iterrows():
                tqdm.write(f"  {row['銘柄コード']}: {row['銘柄名']} - 終値:{row['最新終値']:.0f} (乖離率:{row['高値までの乖離率']:.2f}%)")
        
        tqdm.write(f"✅ 分析完了: {folder_name}")

def main():
    """メイン処理"""
    # inputフォルダ内の全フォルダを取得
    if not os.path.exists(S_INPUT_DIR):
        tqdm.write(f"❌ inputディレクトリが存在しません: {S_INPUT_DIR}")
        return

    # 104週のデータを分析するためのフォルダ名を設定
    # 例: W_52_20250713（52週のデータ、2025年7月13日実行）
    tick_type = TickType.WEEK
    number = 104  # 104週のデータ
    date = "20250918"
    target_folder_name = f"{tick_type.value}_{number}_{date}"
    tqdm.write(f"🔍 分析対象フォルダ名: {target_folder_name}")

    # inputフォルダ内のサブフォルダを検索（market_dataを除外）
    folders = [f for f in os.listdir(S_INPUT_DIR) 
              if os.path.isdir(os.path.join(S_INPUT_DIR, f)) and f != 'market_data']

    # フォルダ名が104週のデータに一致するものをフィルタリング
    folders = [f for f in folders if f.startswith(target_folder_name)]
    
    if not folders:
        tqdm.write("⚠️ 分析対象フォルダがありません。")
        return
    
    # メイン進行状況のプログレスバー
    with tqdm(total=len(folders), desc="� 新高値ブレイク投資法 分析", unit="folder") as main_progress:
        main_progress.set_postfix({"フォルダ数": len(folders)})
        
        # 各フォルダを分析
        for folder_name in folders:
            try:
                main_progress.set_postfix({"現在": folder_name})
                analyze_folder_data(folder_name)
                main_progress.update(1)
            except Exception as e:
                tqdm.write(f"❌ フォルダ {folder_name} の分析でエラーが発生しました: {e}")
                main_progress.update(1)
    
    tqdm.write("\n=== 🎉 分析終了 ===")

if __name__ == "__main__":
    main()