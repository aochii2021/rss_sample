import sys
import os
import pandas as pd

# 親ディレクトリのパスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.data import StockCodeMaster

def debug_stock_code_lookup():
    print("=== 銘柄コード取得デバッグ ===")
    
    # StockCodeMasterを初期化
    stock_master = StockCodeMaster()
    stock_master.load()
    
    # テスト対象の銘柄コード（問題が発生している銘柄）
    test_codes = ['7115', '8957', '3449', '5279', '2971']
    
    print("--- 銘柄マスタ確認 ---")
    for code in test_codes:
        print(f"\n検索対象: '{code}' (型: {type(code)})")
        
        # マスタデータから検索
        result = stock_master.get_by_code(code)
        print(f"検索結果: {len(result)}件")
        
        if not result.empty:
            name = result['name'].iloc[0]
            print(f"  -> 銘柄名: '{name}'")
        else:
            print("  -> 見つかりません")
            
            # マスタに存在する類似コードを探す
            all_codes = stock_master.df['code'].tolist()
            similar_codes = [c for c in all_codes if code in c or c in code]
            print(f"  -> 類似コード: {similar_codes[:5]}")
    
    print("\n--- マスタデータのサンプル確認 ---")
    sample_df = stock_master.df[stock_master.df['code'].isin(test_codes)]
    print(sample_df[['code', 'name']])
    
    print("\n--- 銘柄コードの型とフォーマット確認 ---")
    for code in test_codes:
        # 様々な型とフォーマットでテスト
        formats = [
            code,                # 元の値
            str(code),          # 文字列変換
            str(code).strip(),  # 文字列変換+trim
            f"{code}",          # フォーマット文字列
        ]
        
        for fmt_code in formats:
            result = stock_master.get_by_code(fmt_code)
            status = "✅見つかった" if not result.empty else "❌見つからない"
            print(f"  '{fmt_code}' (型:{type(fmt_code).__name__}) -> {status}")

if __name__ == "__main__":
    debug_stock_code_lookup()
