import sys
import os

# 親ディレクトリのパスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.data import StockCodeMaster

def test_stock_code_master():
    print("=== StockCodeMaster デバッグテスト ===")
    
    # StockCodeMasterを初期化
    stock_master = StockCodeMaster()
    stock_master.load()
    
    print(f"マスタデータの件数: {len(stock_master.df)}")
    print(f"カラム名: {list(stock_master.df.columns)}")
    print("\n--- サンプルデータ（最初の5件）---")
    print(stock_master.df.head())
    
    # テスト対象の銘柄コード
    test_codes = ['7115', '345A', '8957', '3449', '5279', '2971']
    
    print("\n--- 銘柄コード検索テスト ---")
    for code in test_codes:
        result = stock_master.get_by_code(code)
        if not result.empty:
            name = result['name'].iloc[0]
            print(f"銘柄コード: {code} -> 銘柄名: {name}")
        else:
            print(f"銘柄コード: {code} -> 見つかりません")
    
    print("\n--- 銘柄コードの型チェック ---")
    unique_codes = stock_master.df['code'].unique()[:10]
    print(f"マスタデータの銘柄コード例: {unique_codes}")
    print(f"銘柄コードの型: {type(unique_codes[0])}")

if __name__ == "__main__":
    test_stock_code_master()
