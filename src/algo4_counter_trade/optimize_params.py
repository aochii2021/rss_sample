#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
パラメータ最適化スクリプト

グリッドサーチで銘柄ごとに最適なバックテストパラメータを探索
"""
import argparse
import json
import logging
import sys
import itertools
from typing import Dict, List, Tuple, Any
import pandas as pd
import numpy as np

import config
import validation
from backtest_mean_reversion import load_lob_features, load_levels, run_backtest_single_symbol

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# グリッドサーチ用パラメータ範囲
# =============================================================================

PARAM_GRID = {
    "k_tick": [3.0, 5.0, 7.0, 10.0],
    "x_tick": [5.0, 10.0, 15.0, 20.0],
    "y_tick": [3.0, 5.0, 7.0, 10.0],
    "max_hold_bars": [30, 45, 60, 90, 120],
}

# 固定パラメータ（最適化対象外）
FIXED_PARAMS = {
    "roll_n": 20,
    "k_depth": 5
}

# =============================================================================
# 評価関数
# =============================================================================

def calculate_score(trades: List[Dict[str, Any]]) -> float:
    """
    トレード結果からスコアを計算
    
    評価指標：
    - 総PnL（主）
    - 勝率
    - 最大ドローダウン（ペナルティ）
    - トレード数（最低限必要）
    
    Args:
        trades: トレード結果のリスト
    
    Returns:
        スコア（高いほど良い）
    """
    if not trades or len(trades) < 10:
        # トレード数が少なすぎる場合はペナルティ
        return -999999.0
    
    df = pd.DataFrame(trades)
    
    # 総PnL
    total_pnl = df["pnl_tick"].sum()
    
    # 勝率
    win_rate = (df["pnl_tick"] > 0).mean()
    
    # 累積PnLからドローダウン計算
    cumulative_pnl = df["pnl_tick"].cumsum()
    running_max = cumulative_pnl.cummax()
    drawdown = running_max - cumulative_pnl
    max_dd = drawdown.max()
    
    # タイムアウト率（低いほど良い）
    timeout_rate = (df["exit_reason"] == "TO").mean()
    
    # 複合スコア
    # total_pnl が主、win_rate でブースト、max_dd と timeout_rate でペナルティ
    score = (
        total_pnl * 1.0 +          # PnLを重視
        win_rate * 100.0 -          # 勝率ボーナス
        max_dd * 0.5 -              # ドローダウンペナルティ
        timeout_rate * 50.0         # タイムアウトペナルティ
    )
    
    return score

def calculate_metrics_dict(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """トレード結果から詳細メトリクスを計算"""
    if not trades:
        return {
            "num_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "max_dd": 0.0,
            "timeout_rate": 0.0
        }
    
    df = pd.DataFrame(trades)
    
    cumulative_pnl = df["pnl_tick"].cumsum()
    running_max = cumulative_pnl.cummax()
    drawdown = running_max - cumulative_pnl
    
    return {
        "num_trades": len(trades),
        "total_pnl": float(df["pnl_tick"].sum()),
        "win_rate": float((df["pnl_tick"] > 0).mean()),
        "avg_pnl": float(df["pnl_tick"].mean()),
        "max_dd": float(drawdown.max()),
        "timeout_rate": float((df["exit_reason"] == "TO").mean())
    }

# =============================================================================
# グリッドサーチ
# =============================================================================

def grid_search_symbol(
    symbol: str,
    lob: pd.DataFrame,
    levels: List[Dict[str, Any]],
    param_grid: Dict[str, List] = None
) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
    """
    銘柄単位でグリッドサーチ実行
    
    Args:
        symbol: 銘柄コード
        lob: LOB特徴量DataFrame
        levels: S/Rレベルリスト
        param_grid: パラメータグリッド（Noneの場合はデフォルト使用）
    
    Returns:
        (best_params, best_score, best_metrics)
    """
    if param_grid is None:
        param_grid = PARAM_GRID
    
    logger.info(f"Starting grid search for {symbol}...")
    
    # パラメータの全組み合わせ生成
    param_names = list(param_grid.keys())
    param_values = [param_grid[k] for k in param_names]
    combinations = list(itertools.product(*param_values))
    
    logger.info(f"Testing {len(combinations)} parameter combinations")
    
    best_score = -float('inf')
    best_params = None
    best_metrics = None
    
    for i, combo in enumerate(combinations):
        params = dict(zip(param_names, combo))
        params.update(FIXED_PARAMS)
        
        # バックテスト実行
        try:
            trades = run_backtest_single_symbol(
                lob_df=lob,
                levels=levels,
                symbol=symbol,
                **params
            )
            
            score = calculate_score(trades)
            metrics = calculate_metrics_dict(trades)
            
            if score > best_score:
                best_score = score
                best_params = params
                best_metrics = metrics
                logger.info(
                    f"[{i+1}/{len(combinations)}] New best score={score:.2f}, "
                    f"params={params}, metrics={metrics}"
                )
        
        except Exception as e:
            logger.warning(f"Error with params {params}: {e}")
            continue
    
    if best_params is None:
        raise ValueError(f"No valid parameter combination found for {symbol}")
    
    logger.info(f"Grid search completed for {symbol}")
    logger.info(f"Best params: {best_params}")
    logger.info(f"Best score: {best_score:.2f}")
    logger.info(f"Best metrics: {best_metrics}")
    
    return best_params, best_score, best_metrics

# =============================================================================
# メイン処理
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description="パラメータ最適化（グリッドサーチ）")
    ap.add_argument("--lob-features", required=True, help="LOB features CSV")
    ap.add_argument("--levels", required=True, help="S/R levels JSONL")
    ap.add_argument("--symbol", default=None, help="単一銘柄を指定（Noneの場合は全銘柄）")
    ap.add_argument("--out", required=True, help="最適化結果のJSON出力先")
    args = ap.parse_args()
    
    try:
        # データ読み込み
        lob_df = load_lob_features(args.lob_features)
        levels = load_levels(args.levels)
        
        # 銘柄リスト取得
        if args.symbol:
            symbols = [args.symbol]
        else:
            if "symbol" not in lob_df.columns:
                logger.error("LOB features does not have 'symbol' column")
                sys.exit(1)
            all_symbols = lob_df["symbol"].dropna().unique()
            symbols = config.list_active_symbols(all_symbols)
        
        logger.info(f"Optimizing {len(symbols)} symbols: {symbols}")
        
        # 銘柄ごとに最適化
        results = {}
        for symbol in symbols:
            logger.info(f"\n{'='*60}")
            logger.info(f"Optimizing symbol: {symbol}")
            logger.info(f"{'='*60}")
            
            # 銘柄でフィルタ
            lob_sym = lob_df[lob_df["symbol"] == symbol].copy()
            levels_sym = [lv for lv in levels if lv.get("symbol") == symbol]
            
            if lob_sym.empty:
                logger.warning(f"No LOB data for {symbol}, skipping")
                continue
            
            if not levels_sym:
                logger.warning(f"No levels for {symbol}, skipping")
                continue
            
            # グリッドサーチ実行
            best_params, best_score, best_metrics = grid_search_symbol(
                symbol, lob_sym, levels_sym
            )
            
            results[symbol] = {
                "best_params": best_params,
                "best_score": float(best_score),
                "best_metrics": best_metrics
            }
        
        # 結果保存
        validation.ensure_output_directory(args.out)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\nOptimization completed!")
        logger.info(f"Results saved to: {args.out}")
        
        # サマリー表示
        print("\n" + "="*60)
        print("OPTIMIZATION SUMMARY")
        print("="*60)
        for symbol, result in results.items():
            metrics = result["best_metrics"]
            print(f"\n[{symbol}]")
            print(f"  Best Score: {result['best_score']:.2f}")
            print(f"  Total PnL: {metrics['total_pnl']:+.1f} tick")
            print(f"  Win Rate: {metrics['win_rate']*100:.1f}%")
            print(f"  Trades: {metrics['num_trades']}")
            print(f"  Timeout Rate: {metrics['timeout_rate']*100:.1f}%")
            print(f"  Params: k_tick={result['best_params']['k_tick']}, "
                  f"x_tick={result['best_params']['x_tick']}, "
                  f"y_tick={result['best_params']['y_tick']}, "
                  f"max_hold_bars={result['best_params']['max_hold_bars']}")
    
    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
