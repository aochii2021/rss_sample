import pandas as pd
import os

from common import common, columns

class StockCodeMaster:
    def __init__(self, csv_path=None):
        if csv_path is None:
            csv_path = common.S_STOCK_CODE_MASTER_CSV
        self.csv_path = csv_path
        self.df = None

    def load(self):
        """CSVファイルを読み込んでDataFrameとして保持する（日本語→英語カラム名へ変換）"""
        df_jp = pd.read_csv(self.csv_path, encoding='utf-8-sig', dtype="str")
        # 日本語カラム名を英語カラム名に変換
        df_jp = df_jp.rename(columns=columns.JP_TO_EN_STOCK_CODE_MASTER)
        self.df = df_jp[columns.STOCK_CODE_MASTER_COLUMNS]
        return self.df

    def get_by_code(self, code):
        """銘柄コードで検索し、該当する行を返す"""
        if self.df is None:
            self.load()
        return self.df[self.df['code'] == code]

    def get_all_codes(self):
        """全銘柄コードを返す"""
        if self.df is None:
            self.load()
        return self.df['code'].tolist()

    def get_all(self):
        """全データを返す"""
        if self.df is None:
            self.load()
        return self.df
