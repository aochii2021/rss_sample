#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
既存のバックテスト結果からトレードチャートを生成するスクリプト
"""
import sys
import logging
from pathlib import Path
import pandas as pd
import json

# パス設定
sys.path.insert(0, str(Path(__file__).parent))

from output_handlers.visualizer import Visualizer
from core.data_loader import DataLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def _normalize_symbol(symbol: str) -> str:
    """銘柄コード正規化"""
    s = str(symbol)
    if s.endswith('.0'):
        return s[:-2]
    return s


def generate_trade_charts(run_dir: Path) -> None:
    """
    指定されたバックテスト結果ディレクトリからトレードチャートを生成
    
    Args:
        run_dir: バックテスト結果ディレクトリ（例: runs/20260125_005005）
    """
    logger.info(f"トレードチャート生成開始: {run_dir}")
    
    # 出力ディレクトリ
    output_dir = run_dir / "output"
    if not output_dir.exists():
        logger.error(f"output/ディレクトリが見つかりません: {output_dir}")
        return
    
    # trades.csv読み込み
    trades_csv = output_dir / "trades.csv"
    if not trades_csv.exists():
        logger.error(f"trades.csvが見つかりません: {trades_csv}")
        return
    
    trades_df = pd.read_csv(trades_csv)
    if trades_df.empty:
        logger.warning("トレードデータが空です")
        return
    
    logger.info(f"トレード件数: {len(trades_df)}件")
    
    # levels.jsonl読み込み
    levels_jsonl = output_dir / "levels.jsonl"
    all_levels = {}
    if levels_jsonl.exists():
        with open(levels_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                level = json.loads(line)
                symbol = level.get('symbol', '')
                norm_symbol = _normalize_symbol(symbol)
                if norm_symbol not in all_levels:
                    all_levels[norm_symbol] = []
                all_levels[norm_symbol].append(level)
        logger.info(f"レベルデータ読み込み: {len(all_levels)}銘柄")
    
    # DataLoader初期化
    base_dir = Path(__file__).parent
    data_loader = DataLoader(
        chart_data_dir=str(base_dir / "market_data" / "chart_data"),
        market_data_dir=str(base_dir / "market_data" / "market_order_book")
    )
    
    # Visualizer初期化
    visualizer = Visualizer(output_dir)
    
    # トレードがあった銘柄を取得
    symbols_with_trades = trades_df['symbol'].unique()
    load_symbols = [_normalize_symbol(s) for s in symbols_with_trades]
    logger.info(f"トレードチャート生成対象: {len(symbols_with_trades)}銘柄")
    
    # 期間の最終日を取得（全期間のチャートをロード）
    end_date = pd.to_datetime(trades_df['exit_ts'].max()).normalize()
    # 可視化時は当日データを含めるため、cutoff_dateを1日進める
    # （バックテスト実行時は当日を除外してデータリークを防ぐが、
    #   可視化時はトレード既終了なので実績チャートとして当日データも必要）
    cutoff_for_load = end_date + pd.Timedelta(days=1)
    chart_data = data_loader.load_chart_data_until(
        cutoff_date=cutoff_for_load,
        symbols=list(load_symbols),
        allowed_timeframes=['1M', '2M', '3M', '4M', '5M', '10M', '15M', '30M', '60M', '2H', '4H', '8H']
    )
    logger.info(f"チャートデータ読み込み: {len(chart_data)}銘柄")
    
    # 銘柄ごとにチャート生成
    success_count = 0
    for symbol in symbols_with_trades:
        try:
            # その銘柄のトレードを抽出
            symbol_trades = trades_df[trades_df['symbol'] == symbol].copy()
            
            # 正規化されたシンボルでチャートデータを検索
            norm_symbol = _normalize_symbol(symbol)
            if norm_symbol in chart_data:
                chart_df = chart_data[norm_symbol]
            elif symbol in chart_data:
                chart_df = chart_data[symbol]
            else:
                logger.warning(f"  {symbol}: チャートデータなし、スキップ")
                continue
            
            # その銘柄のレベルを取得
            symbol_levels = all_levels.get(norm_symbol, [])
            
            # トレードチャート生成
            output_path = visualizer.plot_trade_chart(
                symbol=symbol,
                chart_df=chart_df,
                trades_df=symbol_trades,
                levels=symbol_levels
            )
            
            if output_path:
                success_count += 1
                logger.info(f"  ✓ {symbol}: {output_path.name}")
            
        except Exception as e:
            logger.error(f"  ✗ {symbol}: {e}", exc_info=True)
    
    logger.info(f"トレードチャート生成完了: {success_count}/{len(symbols_with_trades)}銘柄")


def main():
    """メインエントリーポイント"""
    import argparse
    
    parser = argparse.ArgumentParser(description='バックテスト結果からトレードチャートを生成')
    parser.add_argument('--run-dir', type=str, default='runs/latest',
                       help='バックテスト結果ディレクトリ（デフォルト: runs/latest）')
    
    args = parser.parse_args()
    
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        logger.error(f"ディレクトリが存在しません: {run_dir}")
        sys.exit(1)
    
    try:
        generate_trade_charts(run_dir)
        logger.info("✓ 処理完了")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
