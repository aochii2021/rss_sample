import win32com.client      #エクセル用
import pandas as pd         #データフレーム用
import time                 #時間調整用
from enum import Enum, auto  # 列挙型用

# 抽象クラス
from abc import ABC, abstractmethod


# データ範囲用のデータクラス
from dataclasses import dataclass
from typing import Optional
@dataclass
class DataRange:
    start_row: int
    start_col: int
    end_row: int
    end_col: int

    def __post_init__(self):
        if self.start_row > self.end_row or self.start_col > self.end_col:
            raise ValueError("start_row must be less than or equal to end_row and start_col must be less than or equal to end_col")


class TickType(Enum):
    MIN1 = "1M"
    MIN2 = "2M"
    MIN3 = "3M"
    MIN4 = "4M"
    MIN5 = "5M"
    MIN10 = "10M"
    MIN15 = "15M"
    MIN30 = "30M"
    MIN60 = "60M"
    HOUR2 = "2H"
    HOUR4 = "4H"
    HOUR8 = "8H"
    DAY = "D"
    WEEK = "W"
    MONTH = "M"


class MarketStatusItem(Enum):
    STOCK_CODE = "銘柄コード"
    MARKET_CODE = "市場コード"
    STOCK_NAME = "銘柄名称"
    MARKET_NAME = "市場名称"
    MARKET_DIVISION = "市場部名称"
    MARKET_DIVISION_SHORT = "市場部略称"
    CURRENT_DATE = "現在日付"
    CURRENT_PRICE = "現在値"
    CURRENT_PRICE_TIME = "現在値時刻"
    CURRENT_PRICE_DETAIL_TIME = "現在値詳細時刻"
    CURRENT_PRICE_TICK = "現在値ティック"
    CURRENT_PRICE_FLAG = "現在値フラグ"
    PREV_DAY_DIFF = "前日比"
    PREV_DAY_DIFF_RATE = "前日比率"
    PREV_CLOSE = "前日終値"
    PREV_DATE = "前日日付"
    PREV_CLOSE_FLAG = "前日終値フラグ"
    AYUMI1 = "歩み1"
    AYUMI2 = "歩み2"
    AYUMI3 = "歩み3"
    AYUMI4 = "歩み4"
    AYUMI1_DETAIL_TIME = "歩み1詳細時刻"
    AYUMI2_DETAIL_TIME = "歩み2詳細時刻"
    AYUMI3_DETAIL_TIME = "歩み3詳細時刻"
    AYUMI4_DETAIL_TIME = "歩み4詳細時刻"
    VOLUME = "出来高"
    TRADING_VALUE = "売買代金"
    VWAP = "出来高加重平均"
    MARKET_CAP = "時価総額"
    OPEN = "始値"
    HIGH = "高値"
    LOW = "安値"
    OPEN_TIME = "始値時刻"
    HIGH_TIME = "高値時刻"
    LOW_TIME = "安値時刻"
    OPEN_DETAIL_TIME = "始値詳細時刻"
    HIGH_DETAIL_TIME = "高値詳細時刻"
    LOW_DETAIL_TIME = "安値詳細時刻"
    AM_OPEN = "前場始値"
    AM_HIGH = "前場高値"
    AM_LOW = "前場安値"
    AM_CLOSE = "前場終値"
    AM_VOLUME = "前場出来高"
    PM_OPEN = "後場始値"
    PM_HIGH = "後場高値"
    PM_LOW = "後場安値"
    AM_OPEN_TIME = "前場始値時刻"
    AM_HIGH_TIME = "前場高値時刻"
    AM_LOW_TIME = "前場安値時刻"
    AM_CLOSE_TIME = "前場終値時刻"
    AM_VOLUME_TIME = "前場出来高時刻"
    PM_OPEN_TIME = "後場始値時刻"
    PM_HIGH_TIME = "後場高値時刻"
    PM_LOW_TIME = "後場安値時刻"
    BEST_ASK = "最良売気配値"
    BEST_BID = "最良買気配値"
    BEST_ASK_QTY = "最良売気配数量"
    BEST_BID_QTY = "最良買気配数量"
    BEST_ASK_TIME = "最良売気配時刻"
    BEST_BID_TIME = "最良買気配時刻"
    BEST_ASK_DETAIL_TIME = "最良売気配詳細時刻"
    BEST_BID_DETAIL_TIME = "最良買気配詳細時刻"
    SPECIAL_ASK_FLAG = "特別売気配フラグ"
    SPECIAL_BID_FLAG = "特別買気配フラグ"
    MARGIN_TYPE = "信用貸借区分"
    REVERSE_MARGIN = "逆日歩"
    REVERSE_MARGIN_UPDATE_DATE = "逆日歩更新日付"
    MARGIN_SELL = "信用売残"
    MARGIN_SELL_PREV = "信用売残前週比"
    MARGIN_BUY = "信用買残"
    MARGIN_BUY_PREV = "信用買残前週比"
    MARGIN_RATIO = "信用倍率"
    SHOUKIN_UPDATE_DATE = "証金残更新日付"
    NEW_LENDING = "新規貸株"
    NEW_FINANCING = "新規融資"
    REPAY_LENDING = "返済貸株"
    REPAY_FINANCING = "返済融資"
    BALANCE_LENDING = "残高貸株"
    BALANCE_FINANCING = "残高融資"
    BALANCE_DIFF = "残高差引"
    PREV_LENDING = "前日比貸株"
    PREV_FINANCING = "前日比融資"
    PREV_DIFF = "前日比差引"
    TURNOVER_DAYS = "回転日数"
    LENDING_RATIO = "貸借倍率"
    BEST_ASK1 = "最良売気配値1"
    BEST_ASK2 = "最良売気配値2"
    BEST_ASK3 = "最良売気配値3"
    BEST_ASK4 = "最良売気配値4"
    BEST_ASK5 = "最良売気配値5"
    BEST_ASK6 = "最良売気配値6"
    BEST_ASK7 = "最良売気配値7"
    BEST_ASK8 = "最良売気配値8"
    BEST_ASK9 = "最良売気配値9"
    BEST_ASK10 = "最良売気配値10"
    BEST_BID1 = "最良買気配値1"
    BEST_BID2 = "最良買気配値2"
    BEST_BID3 = "最良買気配値3"
    BEST_BID4 = "最良買気配値4"
    BEST_BID5 = "最良買気配値5"
    BEST_BID6 = "最良買気配値6"
    BEST_BID7 = "最良買気配値7"
    BEST_BID8 = "最良買気配値8"
    BEST_BID9 = "最良買気配値9"
    BEST_BID10 = "最良買気配値10"
    BEST_ASK_QTY1 = "最良売気配数量1"
    BEST_ASK_QTY2 = "最良売気配数量2"
    BEST_ASK_QTY3 = "最良売気配数量3"
    BEST_ASK_QTY4 = "最良売気配数量4"
    BEST_ASK_QTY5 = "最良売気配数量5"
    BEST_ASK_QTY6 = "最良売気配数量6"
    BEST_ASK_QTY7 = "最良売気配数量7"
    BEST_ASK_QTY8 = "最良売気配数量8"
    BEST_ASK_QTY9 = "最良売気配数量9"
    BEST_ASK_QTY10 = "最良売気配数量10"
    BEST_BID_QTY1 = "最良買気配数量1"
    BEST_BID_QTY2 = "最良買気配数量2"
    BEST_BID_QTY3 = "最良買気配数量3"
    BEST_BID_QTY4 = "最良買気配数量4"
    BEST_BID_QTY5 = "最良買気配数量5"
    BEST_BID_QTY6 = "最良買気配数量6"
    BEST_BID_QTY7 = "最良買気配数量7"
    BEST_BID_QTY8 = "最良買気配数量8"
    BEST_BID_QTY9 = "最良買気配数量9"
    BEST_BID_QTY10 = "最良買気配数量10"
    SELL_MARKET_QTY = "売成行数量"
    BUY_MARKET_QTY = "買成行数量"
    OVER_QTY = "OVER気配数量"
    UNDER_QTY = "UNDER気配数量"
    UNIT_SHARES = "単位株数"
    DIVIDEND = "配当"
    DIVIDEND_EX_DATE = "配当落日"
    MID_DIVIDEND_EX_DATE = "中配落日"
    RIGHT_EX_DATE = "権利落日"
    SETTLEMENT_DATE = "決算発表日"
    PER = "PER"
    PBR = "PBR"
    BASE_PRICE = "当日基準値"
    YEAR_HIGH = "年初来高値"
    YEAR_LOW = "年初来安値"
    YEAR_HIGH_DATE = "年初来高値日付"
    YEAR_LOW_DATE = "年初来安値日付"
    IPO_HIGH = "上場来高値"
    IPO_LOW = "上場来安値"
    IPO_HIGH_DATE = "上場来高値日付"
    IPO_LOW_DATE = "上場来安値日付"
    LENDING_RATE = "貸株金利"
    LENDING_RATE_DATE = "貸株金利適用日"


class OrderTrigger(Enum):
    """
    発注トリガー
    """
    FALSE = 0               # 待機
    TRUE = 1                # 発注


class BuySellType(Enum):
    """
    売買区分
    """
    SELL = 1                # 売り
    BUY = 3                 # 買い


class OrderType(Enum):
    """
    注文区分
    """
    NORMAL = 0              # 通常注文
    NORMAL_WITH_STOP = 1    # 逆指値付注文
    STOP_WAIT = 2           # 逆指値付注文（待機中）


class SorType(Enum):
    """
    SOR区分
    """
    NORMAL = 0              # 通常注文
    SOR = 1                 # SOR注文


class MarginType(Enum):
    """
    信用区分
    """
    SYSTEM = 1              # 制度信用（6か月）
    GENERAL_NO_LIMIT = 2    # 一般信用（無制限）
    GENERAL = 3             # 一般信用（14日）
    GENERAL_ONE_DAY = 4     # 一般信用（1日）


class PriceType(Enum):
    """
    価格区分
    """
    MARKET = 0              # 成行
    LIMIT = 1               # 指値


class ExecutionCondition(Enum):
    """
    執行条件
    """
    TODAY = 1               # 当日執行
    THIS_WEEK = 2           # 今週執行
    OPENING = 3             # 寄付
    CLOSING = 4             # 引け
    SCHEDULED = 5           # 期間指定
    LIMIT_OR_MARKET = 6     # 大引不成
    LIMIT_OR_NO = 7         # 不成


class AccountType(Enum):
    """
    口座区分
    """
    SPECIFIC = 0            # 特定
    GENERAL = 1             # 一般


class StopConditionType(Enum):
    """
    逆指値条件区分
    """
    OVER = 1                # 以上
    UNDER = 2               # 以下


class StopPriceType(Enum):
    """
    逆指値価格区分
    """
    MARKET = 0              # 成行
    LIMIT = 1               # 指値


class SetOrderType(Enum):
    """
    セット注文区分
    """
    NORMAL = 0              # 通常
    SET_ORDER = 1           # セット注文


class SetOrderPriceType(Enum):
    """
    セット注文価格区分
    """
    LIMIT = 1               # 指値
    SET_PRICE_WIDTH = 2     # 値幅指定


@dataclass
class MarginOpenOrderParam:
    """
    国内株式 信用新規 パラメータ
    必須・任意の情報をコメントで明示
    """
    # 必須
    order_id: int  # 発注ID（1以上の数値）
    order_trigger: OrderTrigger  # 発注トリガー（0:待機, 1:発注）
    stock_code: str  # 銘柄コード（例: 7203.T）
    buy_sell_type: BuySellType  # 売買区分（1:売り, 3:買い）
    order_type: OrderType  # 注文区分（0:通常, 1:逆指値付, 2:逆指値待機）
    sor_type: SorType  # SOR区分（0:通常, 1:SOR）
    margin_type: MarginType  # 信用区分（1:制度, 2:一般無制限, 3:一般14日, 4:一般いちにち）
    order_quantity: int  # 注文数量
    execution_condition: ExecutionCondition  # 執行条件（1:本日中 など）
    account_type: AccountType  # 口座区分（0:特定, 1:一般）

    # 任意
    price_type: Optional[PriceType] = None  # 価格区分（0:成行, 1:指値）
    order_price: Optional[float] = None  # 注文価格
    order_deadline_date: Optional[str] = None  # 注文期限（YYYYMMDD）
    stop_condition_price: Optional[float] = None  # 逆指値条件価格
    stop_condition_type: Optional[StopConditionType] = None  # 逆指値条件区分（1:以上, 2:以下）
    stop_price_type: Optional[StopPriceType] = None  # 逆指値価格区分（0:成行, 1:指値）
    stop_price: Optional[float] = None  # 逆指値価格
    set_order_type: Optional[SetOrderType] = None  # セット注文区分（0:通常, 1:セット）
    set_order_price_type: Optional[SetOrderPriceType] = None  # セット注文価格区分（1:指値, 2:値幅指定）
    set_order_price: Optional[float] = None  # セット注文価格
    set_order_execution_condition: Optional[ExecutionCondition] = None  # セット注文執行条件
    set_order_deadline_date: Optional[str] = None  # セット注文期限（YYYYMMDD）

    def validate(self):
        errors = []
        # 1 発注ID 必須
        if not self.order_id:
            errors.append("発注ID(order_id)は必須です。")
        # 2 発注トリガー 必須
        if self.order_trigger is None:
            errors.append("発注トリガー(order_trigger)は必須です。")
        # 3 銘柄コード 必須
        if not self.stock_code:
            errors.append("銘柄コード(stock_code)は必須です。")
        # 4 売買区分 必須
        if not self.buy_sell_type:
            errors.append("売買区分(buy_sell_type)は必須です。")
        # 5 注文区分 必須
        if not self.order_type:
            errors.append("注文区分(order_type)は必須です。")
        # 6 SOR区分 必須
        if not self.sor_type:
            errors.append("SOR区分(sor_type)は必須です。")
        # 7 信用区分 必須
        if not self.margin_type:
            errors.append("信用区分(margin_type)は必須です。")
        # 8 注文数量 必須
        if not self.order_quantity:
            errors.append("注文数量(order_quantity)は必須です。")
        # 9,10 価格区分・注文価格（注文区分が0または1の場合は必須）
        if self.order_type in [OrderType.NORMAL, OrderType.NORMAL_WITH_STOP]:
            if not self.price_type:
                errors.append("注文区分が通常注文または逆指値付き通常注文の場合、価格区分(price_type)は必須です。")
            if self.price_type is None:
                errors.append("注文区分が通常注文または逆指値付き通常注文の場合、注文価格(price)は必須です。")
        # 11 執行条件 必須
        if not self.execution_condition:
            errors.append("執行条件(execution_condition)は必須です。")
        # 12 注文期限（執行条件が5の場合は必須）
        if self.execution_condition == ExecutionCondition.SCHEDULED and not self.order_deadline_date:
            errors.append("執行条件が5:期間指定の場合、注文期限(order_deadline_date)は必須です。")
        # 13 口座区分 必須
        if not self.account_type:
            errors.append("口座区分(account_type)は必須です。")
        # 14-17 逆指値関連（注文区分が1または2の場合は必須）
        if self.order_type in [OrderType.NORMAL, OrderType.NORMAL_WITH_STOP]:
            if self.stop_price is None:
                errors.append("注文区分が1または2の場合、逆指値条件価格(stop_price)は必須です。")
            if not self.stop_price_type:
                errors.append("注文区分が1または2の場合、逆指値条件区分(stop_price_type)は必須です。")
            if not self.stop_price_type:
                errors.append("注文区分が1または2の場合、逆指値価格区分(stop_price_type)は必須です。")
            if self.stop_price is None:
                errors.append("注文区分が1または2の場合、逆指値価格(stop_price)は必須です。")
        # 18-20 セット注文関連（セット注文区分が1の場合は必須）
        if self.set_order_type == SetOrderPriceType.LIMIT:
            if not self.set_order_price_type:
                errors.append("セット注文区分が1の場合、セット注文価格区分(set_order_price_type)は必須です。")
            if self.set_order_price is None:
                errors.append("セット注文区分が1の場合、セット注文価格(set_order_price)は必須です。")
        if errors:
            raise ValueError('\n'.join(errors))


@dataclass
class MarginCloseOrderParam:
    # 必須
    order_id: int
    order_trigger: OrderTrigger
    stock_code: str
    buy_sell_type: BuySellType
    order_type: OrderType
    sor_type: SorType
    margin_type: MarginType
    order_quantity: int
    execution_condition: ExecutionCondition
    account_type: AccountType
    opening_date: str
    opening_price: float
    opening_market: int

    # 任意
    price_type: Optional[PriceType] = None
    order_price: Optional[float] = None
    order_deadline_date: Optional[str] = None
    stop_condition_price: Optional[float] = None
    stop_condition_type: Optional[StopConditionType] = None
    stop_price_type: Optional[StopPriceType] = None
    stop_price: Optional[float] = None

    def validate(self):
        errors = []
        if not self.order_id:
            errors.append("発注ID(order_id)は必須です。")
        if self.order_trigger is None:
            errors.append("発注トリガー(order_trigger)は必須です。")
        if not self.stock_code:
            errors.append("銘柄コード(stock_code)は必須です。")
        if not self.buy_sell_type:
            errors.append("売買区分(buy_sell_type)は必須です。")
        if not self.order_type:
            errors.append("注文区分(order_type)は必須です。")
        if not self.sor_type:
            errors.append("SOR区分(sor_type)は必須です。")
        if not self.margin_type:
            errors.append("信用区分(margin_type)は必須です。")
        if not self.order_quantity:
            errors.append("注文数量(order_quantity)は必須です。")
        if self.order_type in [OrderType.NORMAL, OrderType.NORMAL_WITH_STOP]:
            if not self.price_type:
                errors.append("注文区分が通常注文または逆指値付き通常注文の場合、価格区分(price_type)は必須です。")
            if self.price_type is None:
                errors.append("注文区分が通常注文または逆指値付き通常注文の場合、注文価格(order_price)は必須です。")
        if not self.execution_condition:
            errors.append("執行条件(execution_condition)は必須です。")
        if self.execution_condition == ExecutionCondition.SCHEDULED and not self.order_deadline_date:
            errors.append("執行条件が5:期間指定の場合、注文期限(order_deadline_date)は必須です。")
        if not self.account_type:
            errors.append("口座区分(account_type)は必須です。")
        if not self.opening_date:
            errors.append("建日(opening_date)は必須です。")
        if self.opening_price is None:
            errors.append("建単価(opening_price)は必須です。")
        if self.opening_market is None:
            errors.append("建市場(opening_market)は必須です。")
        if self.order_type in [OrderType.NORMAL_WITH_STOP, OrderType.STOP_WAIT]:
            if self.stop_condition_price is None:
                errors.append("注文区分が1または2の場合、逆指値条件価格(stop_condition_price)は必須です。")
            if not self.stop_condition_type:
                errors.append("注文区分が1または2の場合、逆指値条件区分(stop_condition_type)は必須です。")
            if not self.stop_price_type:
                errors.append("注文区分が1または2の場合、逆指値価格区分(stop_price_type)は必須です。")
            if self.stop_price is None:
                errors.append("注文区分が1または2の場合、逆指値価格(stop_price)は必須です。")
        if errors:
            raise ValueError('\n'.join(errors))


class RssBase(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def create_formula(self) -> str:
        """
        抽象メソッド: RSS関数を作成する
        :param stock_code: 銘柄コード
        :param item: 取得したいデータの項目
        :return: RSS関数の文字列
        """
        pass

    @abstractmethod
    def is_valid(self) -> bool:
        """
        抽象メソッド: 取得結果が有効かどうかを判定する
        :return: True if valid, False otherwise
        """
        pass


class RssMarket(RssBase):
    def __init__(self, ws, stock_code_list: list[str], item_list: list[MarketStatusItem]):
        """
        コンストラクタ
        :param ws: Excelのワークシートオブジェクト
        :param stock_code_list: 銘柄コードのリスト
        :param item_list: 取得したいデータの項目
        """
        self.ws = ws
        self.stock_code_list = stock_code_list
        self.item_list = item_list
        self.batch_row_size = min(2000 // len(item_list), len(stock_code_list)) # 1回のRSS関数で取得するデータ量を調整
        self.range = ws.Range(
            ws.Cells(1, 1),
            ws.Cells(self.batch_row_size, len(item_list))
        )

    def create_formula(self, stock_code: str, item: MarketStatusItem) -> str:
        return f'=RssMarket("{stock_code}", "{item.value}")'

    def is_valid(self) -> bool:
        try:
            # 最後の行のステータスをチェック
            print(f"batch_row_size: {self.batch_row_size}")
            status_str = self.ws.Cells(self.batch_row_size, 1).Value
            if status_str == "":
                return False
            return True
        except Exception as e:
            print(f"Error checking validity: {e}")
            return False

    def get_dataframe(self) -> pd.DataFrame:
        # シート全体をクリア
        self.ws.Cells.ClearContents()
        # ヘッダーを取得
        headers = [item.value for item in self.item_list]
        l_df = []
        for batch_start in range(0, len(self.stock_code_list), self.batch_row_size):
            # バッチごとに銘柄コードを取得
            batch_end = min(batch_start + self.batch_row_size, len(self.stock_code_list))
            batch_stock_codes = self.stock_code_list[batch_start:batch_end]
            for i, item in enumerate(self.item_list):
                for j, stock_code in enumerate(batch_stock_codes):
                    # RSS関数を設定
                    formula = self.create_formula(stock_code, item)
                    print(f"RSS関数: {formula}")
                    while True:
                        try:
                            # セルにRSS関数を設定
                            self.ws.Cells(1 + j, 1 + i).Formula = formula
                            break  # 成功したらループを抜ける
                        except Exception as e:
                            print(f"Error setting formula: {e}, 再試行中...")
                            time.sleep(1)

            # 取得結果が有効になるまで待機
            max_retries = 100
            retries = 0
            while not self.is_valid() and retries < max_retries:
                print("RSS関数のステータスが有効になるまで待機中...")
                time.sleep(1)
                retries += 1
            time.sleep(2)  # 少し待機してからデータを取得
            # データを取得
            while True:
                try:
                    # データを取得
                    data = self.range.Value
                    break  # 成功したらループを抜ける
                except Exception as e:
                    print(f"Error getting range: {e}, 再試行中...")
                    time.sleep(1)
            if data is None:
                print("データが取得できませんでした。")
                return pd.DataFrame(columns=headers)
            # データフレームを作成
            df = pd.DataFrame(data, columns=headers)
            l_df.append(df)
        return pd.concat(l_df, ignore_index=True)


class RssList(RssBase):
    def __init__(self, ws, stock_code: str, number: int, data_range: DataRange, header_row: int):
        """
        コンストラクタ
        :param ws: Excelのワークシートオブジェクト
        :param stock_code: 銘柄コード
        :param number: 取得するデータの数
        """
        self.ws = ws
        self.stock_code = stock_code
        self.number = number
        self.range = ws.Range(
            ws.Cells(data_range.start_row, data_range.start_col),
            ws.Cells(data_range.end_row, data_range.end_col)
        )
        self.data_range = data_range
        self.header_row = header_row

    def create_formula(self) -> str:
        """
        RSS関数を作成する
        :return: RSS関数の文字列
        """
        pass

    def is_valid(self) -> bool:
        """
        取得結果が有効かどうかを判定する（ステータスが「応答待ち」以外）
        :return: True if valid, False otherwise
        """
        try:
            status_str = self.ws.Cells(1, 1).Value
            status = status_str.split('=>')[-1].strip()
            return status != "応答待ち"
        except Exception as e:
            print(f"Error checking validity: {e}")
            return False

    def get_headers(self) -> list:
        """
        ヘッダーを取得する
        :return: ヘッダーのリスト
        """
        self.headers = [cell.Value for cell in self.ws.Range(
            self.ws.Cells(self.header_row, self.data_range.start_col),
            self.ws.Cells(self.header_row, self.data_range.end_col)
        )]
        return self.headers 

    def get_dataframe(self) -> pd.DataFrame:
        """
        データフレームを取得する
        :return: pandas DataFrame
        """
        formula = self.create_formula()
        print(f"RSS関数: {formula}")
        # シート全体をクリア
        self.ws.Cells.ClearContents()
        self.ws.Cells(1, 1).Formula = formula
        # ステータスが「応答待ち」以外になるまで待機
        while not self.is_valid():
            print("RSS関数のステータスが「応答待ち」以外になるまで待機中...")
            time.sleep(1)
        # データを取得
        headers = self.get_headers()
        data = self.range.Value

        df = pd.DataFrame(data, columns=headers)
        return df


class RssChart(RssList):
    def __init__(self, ws, stock_code: str, bar: str, number: int, data_range: DataRange, header_row: int):
        super().__init__(ws, stock_code, number, data_range, header_row)
        self.bar = bar

    def create_formula(self) -> str:
        return f'=RssChart(,"{self.stock_code}", "{self.bar}", {self.number})'


class RssTickList(RssList):
    def __init__(self, ws, stock_code: str, number: int, data_range: DataRange, header_row: int):
        super().__init__(ws, stock_code, number, data_range, header_row)

    def create_formula(self) -> str:
        return f'=RssTickList(,{self.stock_code}, {self.number})'


class RssTrendSma(RssList):
    def __init__(self, ws, stock_code: str, bar: str, number: int, data_range: DataRange, header_row: int,
                 window1: int = 5, window2: int = 25, window3: int = 75):
        super().__init__(ws, stock_code, number, data_range, header_row)
        self.bar = bar
        self.window1 = window1
        self.window2 = window2
        self.window3 = window3

    def create_formula(self) -> str:
        return f'=RssTrendSMA(,"{self.stock_code}", "{self.bar}", {self.number}, {self.window1}, {self.window2}, {self.window3})'


class RssMarginOpenOrder(RssBase):
    def __init__(self, ws, stock_code: str):
        super().__init__(ws, stock_code)

    def create_formula(self) -> str:
        return f'=RssMarginOpenOrder(,"{self.stock_code}")'


def main():
    try:
        xl = win32com.client.GetObject(Class="Excel.Application")  # 今、開いている空白のブック
    except Exception as e:
        print("エクセルが開いていません。", e)
        return

    xl.Visible = True
    ws = xl.Worksheets('Sheet1')

    # 銘柄コード、足種、表示本数を設定
    stock_code = 7203  # トヨタ自動車の例
    bar = "D"  # 日足
    number = 50  # 表示本数
    header_row = 2
    rss_chart_range = DataRange(start_row=3, start_col=4, end_row=number + 2, end_col=10)

    rss_chart = RssChart(ws, stock_code, bar, number, rss_chart_range, header_row)
    df = rss_chart.get_dataframe()
    # データフレームを表示
    print(df)

    # ティッカーの取得
    rss_tick_list_range = DataRange(start_row=3, start_col=1, end_row=number + 2, end_col=3)
    rss_tick_list = RssTickList(ws, stock_code, number, rss_tick_list_range, header_row)
    tick_df = rss_tick_list.get_dataframe()
    # データフレームを表示
    print(tick_df)
    
if __name__ == "__main__":
    main()
# このコードは、RSSを使用して株価チャートを取得し、Excelに表示するサンプルです。