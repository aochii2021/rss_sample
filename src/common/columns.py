from dataclasses import dataclass

# 日本語カラム名と英語カラム名のマッピング
JP_TO_EN_STOCK_CODE_MASTER = {
    "日付": "date",
    "コード": "code",
    "銘柄名": "name",
    "市場・商品区分": "market",
    "33業種コード": "industry33_code",
    "33業種区分": "industry33_name",
    "17業種コード": "industry17_code",
    "17業種区分": "industry17_name",
    "規模コード": "scale_code",
    "規模区分": "scale_name"
}

@dataclass
class StockCodeMasterRecord:
    date: str
    code: str
    name: str
    market: str
    industry33_code: str
    industry33_name: str
    industry17_code: str
    industry17_name: str
    scale_code: str
    scale_name: str

# 株価コードマスターCSVのカラム名定義
STOCK_CODE_MASTER_COLUMNS = list(JP_TO_EN_STOCK_CODE_MASTER.values())
