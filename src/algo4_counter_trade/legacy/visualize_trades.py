#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
既存バックテスト結果の銘柄別トレード可視化スクリプト

使用例:
    python visualize_trades.py runs/20260124_204757
"""

import sys
import logging
import json
from pathlib import Path
import pandas as pd

# モジュールパス追加
sys.path.insert(0, str(Path(__file__).parent))

from output_handlers.visualizer import Visualizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    
    # コマンドライン引数から結果ディレクトリを取得
    if len(sys.argv) > 1:
        result_dir = Path(sys.argv[1])
    else:
        # デフォルトは最新の結果ディレクトリ
        runs_dir = Path(__file__).parent / "runs"
        result_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], reverse=True)
        if not result_dirs:
            logger.error("結果ディレクトリが見つかりません")
            return
        result_dir = result_dirs[0]
    
    logger.info(f"結果ディレクトリ: {result_dir}")
    
    # trades.csvを読み込み
    trades_csv = result_dir / "output" / "trades.csv"
    if not trades_csv.exists():
        logger.error(f"trades.csvが見つかりません: {trades_csv}")
        return
    
    trades_df = pd.read_csv(trades_csv)
    logger.info(f"トレード数: {len(trades_df)}")
    
    if len(trades_df) == 0:
        logger.warning("トレードデータが空です")
        return
    
    # 銘柄別に集計
    symbols = trades_df['symbol'].unique()
    logger.info(f"トレードが発生した銘柄: {len(symbols)}銘柄")
    for symbol in symbols:
        symbol_trades = trades_df[trades_df['symbol'] == symbol]
        logger.info(f"  - {symbol}: {len(symbol_trades)}件")
    
    # チャートデータのパス
    chart_data_path = Path(__file__).parent / "market_data" / "chart_data"
    if not chart_data_path.exists():
        logger.error(f"チャートデータディレクトリが見つかりません: {chart_data_path}")
        return
    
    # レベルデータの読み込み
    levels_jsonl = result_dir / "output" / "levels.jsonl"
    levels_df = None
    if levels_jsonl.exists():
        try:
            # JSONLファイルを読み込み
            levels_data = []
            with open(levels_jsonl, 'r', encoding='utf-8') as f:
                for line in f:
                    levels_data.append(json.loads(line.strip()))
            levels_df = pd.DataFrame(levels_data)
            logger.info(f"レベルデータ読み込み完了: {len(levels_df)}件")
        except Exception as e:
            logger.warning(f"レベルデータ読み込みエラー: {e}")
    else:
        logger.warning(f"levels.jsonlが見つかりません: {levels_jsonl}")
    
    # Visualizerで銘柄別トレードチャートを生成
    output_dir = result_dir / "output"
    visualizer = Visualizer(output_dir)
    
    logger.info("銘柄別トレードチャート生成開始...")
    output_files = visualizer.plot_all_symbol_trades(trades_df, chart_data_path, levels_df)
    
    logger.info(f"\n=== 生成完了 ===")
    for name, path in output_files.items():
        logger.info(f"  {path}")
    
    logger.info(f"\n✓ 銘柄別トレードチャート生成完了: {len(output_files)}ファイル")


if __name__ == "__main__":
    main()
