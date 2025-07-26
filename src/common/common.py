# data/stock_code_master.csv の絶対パスを設定
import os

# プロジェクトルートからの相対パスを絶対パスに変換
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_current_dir))
S_STOCK_CODE_MASTER_CSV = os.path.join(_project_root, "data", "stock_code_master.csv")