#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
統合テストスクリプト

統合バックテストシステムの基本機能を検証:
1. 設定ファイルの読み込み
2. コンポーネントの初期化
3. 短期間バックテストの実行
4. 出力ファイルの確認
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from utils.config_validator import ConfigValidator
from utils.date_utils import DateUtils
from core.data_loader import DataLoader
from core.level_generator import LevelGenerator
from processors.lob_processor import LOBProcessor

logger = logging.getLogger(__name__)


def test_config_loading():
    """設定ファイル読み込みテスト"""
    print("=" * 60)
    print("Test 1: 設定ファイル読み込み")
    print("=" * 60)
    
    try:
        base_dir = Path(__file__).parent
        
        # バックテスト設定
        backtest_config = ConfigValidator.load_backtest_config(
            str(base_dir / "config" / "backtest_config.yaml")
        )
        print(f"✓ バックテスト設定読み込み成功")
        print(f"  - mode: {backtest_config['mode']}")
        print(f"  - 期間: {backtest_config['backtest']['start_date']} ～ {backtest_config['backtest']['end_date']}")
        
        # レベル設定
        level_config = ConfigValidator.load_level_config(
            str(base_dir / "config" / "level_config.yaml")
        )
        enabled_types = ConfigValidator.get_enabled_level_types(level_config)
        print(f"✓ レベル設定読み込み成功")
        print(f"  - 有効タイプ: {enabled_types}")
        
        # データパス検証
        ConfigValidator.validate_data_paths(backtest_config, base_dir)
        print(f"✓ データパス検証成功")
        
        return True
    except Exception as e:
        print(f"✗ エラー: {e}")
        return False


def test_component_initialization():
    """コンポーネント初期化テスト"""
    print("\n" + "=" * 60)
    print("Test 2: コンポーネント初期化")
    print("=" * 60)
    
    try:
        base_dir = Path(__file__).parent
        backtest_config = ConfigValidator.load_backtest_config(
            str(base_dir / "config" / "backtest_config.yaml")
        )
        level_config = ConfigValidator.load_level_config(
            str(base_dir / "config" / "level_config.yaml")
        )
        
        # DataLoader
        data_loader = DataLoader(
            chart_data_dir=str(base_dir / backtest_config['data']['chart_data_dir']),
            market_data_dir=str(base_dir / backtest_config['data']['market_data_dir'])
        )
        print(f"✓ DataLoader初期化成功")
        
        # LevelGenerator
        level_generator = LevelGenerator(level_config=level_config)
        print(f"✓ LevelGenerator初期化成功")
        
        # LOBProcessor
        lob_processor = LOBProcessor()
        print(f"✓ LOBProcessor初期化成功")
        
        return True
    except Exception as e:
        print(f"✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_loading():
    """データ読み込みテスト"""
    print("\n" + "=" * 60)
    print("Test 3: データ読み込み")
    print("=" * 60)
    
    try:
        base_dir = Path(__file__).parent
        backtest_config = ConfigValidator.load_backtest_config(
            str(base_dir / "config" / "backtest_config.yaml")
        )
        
        data_loader = DataLoader(
            chart_data_dir=str(base_dir / backtest_config['data']['chart_data_dir']),
            market_data_dir=str(base_dir / backtest_config['data']['market_data_dir'])
        )
        
        # テスト対象日（直近の営業日）
        test_date = datetime.now() - timedelta(days=1)
        
        # チャートデータ読み込み
        chart_data = data_loader.load_chart_data_until(test_date, lookback_days=5)
        print(f"✓ チャートデータ読み込み: {len(chart_data)}銘柄")
        
        # 板情報読み込み
        market_data = data_loader.load_market_data_for_date(test_date)
        print(f"✓ 板情報データ読み込み: {len(market_data)}銘柄")
        
        # データ内容確認
        if market_data:
            sample_symbol = list(market_data.keys())[0]
            sample_df = market_data[sample_symbol]
            print(f"  サンプル（{sample_symbol}）: {len(sample_df)}行, {len(sample_df.columns)}カラム")
        
        return True
    except Exception as e:
        print(f"✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_leak_prevention():
    """データリーク防止テスト"""
    print("\n" + "=" * 60)
    print("Test 4: データリーク防止")
    print("=" * 60)
    
    try:
        base_dir = Path(__file__).parent
        backtest_config = ConfigValidator.load_backtest_config(
            str(base_dir / "config" / "backtest_config.yaml")
        )
        
        data_loader = DataLoader(
            chart_data_dir=str(base_dir / backtest_config['data']['chart_data_dir']),
            market_data_dir=str(base_dir / backtest_config['data']['market_data_dir'])
        )
        
        # カットオフ日
        cutoff_date = datetime(2026, 1, 20)
        
        # チャートデータ読み込み
        chart_data = data_loader.load_chart_data_until(cutoff_date, lookback_days=5)
        
        # 未来データが含まれていないか確認
        leak_found = False
        for symbol, df in chart_data.items():
            if df.empty:
                continue
            
            # 日付カラムを探す
            date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower() or 'timestamp' in col.lower()]
            if not date_cols:
                continue
            
            date_col = date_cols[0]
            max_date = df[date_col].max()
            if isinstance(max_date, str):
                max_date = datetime.fromisoformat(max_date.split()[0])
            
            if max_date > cutoff_date:
                print(f"✗ データリーク検出: {symbol}, 最大日付={max_date} > カットオフ={cutoff_date}")
                leak_found = True
        
        if not leak_found:
            print(f"✓ データリーク防止確認完了: カットオフ日={cutoff_date.strftime('%Y-%m-%d')}")
        
        return not leak_found
    except Exception as e:
        print(f"✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_output_structure():
    """出力ファイル構造テスト"""
    print("\n" + "=" * 60)
    print("Test 5: 出力ファイル構造")
    print("=" * 60)
    
    try:
        base_dir = Path(__file__).parent
        output_dir = base_dir / "output"
        
        if not output_dir.exists():
            print(f"✗ 出力ディレクトリが存在しません: {output_dir}")
            return False
        
        # 最新の出力ディレクトリを探す
        output_subdirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith('202')]
        if not output_subdirs:
            print(f"✗ 出力サブディレクトリが見つかりません")
            return False
        
        latest_dir = max(output_subdirs, key=lambda d: d.name)
        print(f"最新出力ディレクトリ: {latest_dir.name}")
        
        # 必須ファイルの確認
        required_files = [
            'trades.csv',
            'summary.json',
            'levels.jsonl',
            'backtest_config_snapshot.yaml',
            'level_config_snapshot.yaml',
            'backtest.log'
        ]
        
        missing_files = []
        for file_name in required_files:
            file_path = latest_dir / file_name
            if file_path.exists():
                print(f"  ✓ {file_name}: {file_path.stat().st_size} bytes")
            else:
                print(f"  ✗ {file_name}: 見つかりません")
                missing_files.append(file_name)
        
        # グラフファイルの確認（任意）
        graph_files = [
            'pnl_curve.png',
            'pnl_distribution.png',
            'symbol_performance.png',
            'exit_reason_breakdown.png',
            'hold_time_distribution.png'
        ]
        
        for file_name in graph_files:
            file_path = latest_dir / file_name
            if file_path.exists():
                print(f"  ✓ {file_name}: {file_path.stat().st_size} bytes")
        
        return len(missing_files) == 0
    except Exception as e:
        print(f"✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メインテスト実行"""
    logging.basicConfig(
        level=logging.WARNING,  # テスト中は警告以上のみ表示
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "=" * 60)
    print("統合バックテストシステム - 統合テスト")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: 設定ファイル読み込み
    results.append(("設定ファイル読み込み", test_config_loading()))
    
    # Test 2: コンポーネント初期化
    results.append(("コンポーネント初期化", test_component_initialization()))
    
    # Test 3: データ読み込み
    results.append(("データ読み込み", test_data_loading()))
    
    # Test 4: データリーク防止
    results.append(("データリーク防止", test_data_leak_prevention()))
    
    # Test 5: 出力ファイル構造
    results.append(("出力ファイル構造", test_output_structure()))
    
    # 結果サマリ
    print("\n" + "=" * 60)
    print("テスト結果サマリ")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print()
    print(f"合計: {len(results)}件")
    print(f"成功: {passed}件")
    print(f"失敗: {failed}件")
    
    if failed == 0:
        print("\n[SUCCESS] 全てのテストが成功しました")
        return 0
    else:
        print(f"\n[FAILURE] {failed}件のテストが失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
