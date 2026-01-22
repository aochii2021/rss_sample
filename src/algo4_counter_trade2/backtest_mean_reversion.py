#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
逆張り（ミーンリバージョン）バックテスト
LOB特徴量 + S/Rレベルを用いた反転戦略
"""
import argparse
import json
import logging
import sys
from typing import List, Dict, Any
import pandas as pd
import numpy as np

import config
import validation

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def load_lob_features(path: str) -> pd.DataFrame:
    """LOB特徴量の読み込みと検証"""
    validation.validate_csv_columns(path, config.REQUIRED_COLUMNS["lob_features"])
    df = pd.read_csv(path)
    df["ts"] = pd.to_datetime(df["ts"])
    logger.info(f"Loaded LOB features: {len(df)} rows")
    return df.sort_values("ts").reset_index(drop=True)

def load_levels(path: str) -> List[Dict[str, Any]]:
    """S/Rレベルの読み込みと検証"""
    validation.validate_file_exists(path)
    with open(path, "r", encoding="utf-8") as f:
        levels = [json.loads(line) for line in f]
    validation.validate_levels(levels)
    logger.info(f"Loaded levels: {len(levels)} levels")
    return levels

def is_near_level(price: float, level: float, k_tick: float) -> bool:
    """価格がレベルの反応帯内か判定"""
    return abs(price - level) <= k_tick

def get_trading_session(ts) -> str:
    """
    取引セッションを判定
    
    Returns:
        'morning': 前場 (9:00-11:30)
        'afternoon': 後場 (12:30-15:15)
        'closed': 場外
    """
    if not hasattr(ts, 'hour'):
        return 'closed'
    
    hour = ts.hour
    minute = ts.minute
    
    # 前場: 9:00 - 11:30
    if (hour == 9 and minute >= 0) or (hour == 10) or (hour == 11 and minute <= 30):
        return 'morning'
    
    # 後場: 12:30 - 15:15
    if (hour == 12 and minute >= 30) or (hour == 13) or (hour == 14) or (hour == 15 and minute <= 15):
        return 'afternoon'
    
    return 'closed'

def is_session_end_approaching(ts, session: str, minutes_before: int = 5) -> bool:
    """
    セッション終了が近づいているか判定
    """
    if not hasattr(ts, 'hour'):
        return False
    
    hour = ts.hour
    minute = ts.minute
    
    if session == 'morning':
        # 11:30の5分前 = 11:25
        return hour == 11 and minute >= (30 - minutes_before)
    elif session == 'afternoon':
        # 15:15の5分前 = 15:10
        return hour == 15 and minute >= (15 - minutes_before)
    
    return False

def detect_recent_drop(lob_df: pd.DataFrame, current_idx: int, lookback: int = 10) -> tuple:
    """
    直近の急落を検出
    
    Returns:
        (has_drop, high_price, low_price, drop_size)
    """
    if current_idx < lookback:
        return False, 0.0, 0.0, 0.0
    
    recent_slice = lob_df.iloc[max(0, current_idx - lookback):current_idx + 1]
    if len(recent_slice) < 2:
        return False, 0.0, 0.0, 0.0
    
    high_price = recent_slice['mid'].max()
    low_price = recent_slice['mid'].min()
    drop_size = high_price - low_price
    
    # 直近の最安値が現在から3本以内にある場合は「急落中」とみなす
    low_idx = recent_slice['mid'].idxmin()
    bars_since_low = current_idx - low_idx
    
    # 急落判定：下落幅が大きく、かつ最安値が最近（厳格化：>7 tick）
    has_drop = drop_size > 7.0 and bars_since_low <= 3
    
    return has_drop, high_price, low_price, drop_size

def find_next_resistance(price: float, direction: str, levels: List[Dict]) -> float:
    """
    次のレジスタンスレベルを検索
    
    Args:
        price: 現在価格
        direction: "buy" or "sell"
        levels: レベルリスト
    
    Returns:
        次のレジスタンス価格（見つからない場合はNone）
    """
    if direction == "buy":
        # 買いポジション：現在価格より上のレベル
        upper_levels = [lv['level_now'] for lv in levels if lv['level_now'] > price]
        if upper_levels:
            return min(upper_levels)  # 最も近い上のレベル
    else:
        # 売りポジション：現在価格より下のレベル
        lower_levels = [lv['level_now'] for lv in levels if lv['level_now'] < price]
        if lower_levels:
            return max(lower_levels)  # 最も近い下のレベル
    
    return None

def is_reversal_weakening(row, direction: str, ofi_col: str, depth_col: str) -> bool:
    """
    反発が弱まっているか判定
    
    Args:
        row: 現在の行データ
        direction: "buy" or "sell"
        ofi_col: OFIカラム名
        depth_col: depth_imbカラム名
    
    Returns:
        反発が弱まっている場合True
    """
    ofi = row.get(ofi_col, 0)
    depth_imb = row.get(depth_col, 0)
    
    if direction == "buy":
        # 買いポジション：OFIが負（売り圧力）、depth_imbが負（売り板厚い）
        return ofi < -0.3 and depth_imb < -0.2
    else:
        # 売りポジション：OFIが正（買い圧力）、depth_imbが正（買い板厚い）
        return ofi > 0.3 and depth_imb > 0.2

def is_reversal_failing(row, direction: str, micro_bias_col: str, ofi_col: str, depth_col: str) -> bool:
    """
    反転シグナルが消失しているか判定（含み損時の早期損切り用）
    
    Args:
        row: 現在の行データ
        direction: "buy" or "sell"
        micro_bias_col: micro_biasカラム名
        ofi_col: OFIカラム名
        depth_col: depth_imbカラム名
    
    Returns:
        反転が失敗している（逆方向の圧力が強い）場合True
    """
    micro_bias = row.get(micro_bias_col, 0)
    ofi = row.get(ofi_col, 0)
    depth_imb = row.get(depth_col, 0)
    
    if direction == "buy":
        # 買いポジションで含み損：下落圧力が強い = 反転失敗
        # OFIとdepth_imbのどちらかが逆方向に強く振れている場合
        has_sell_pressure = ofi < -0.2 or depth_imb < -0.15
        # micro_biasも負なら確実に反転失敗
        if micro_bias < -0.2 and has_sell_pressure:
            return True
        # OFIとdepth_imbが両方とも逆方向の場合
        return ofi < -0.15 and depth_imb < -0.15
    else:
        # 売りポジションで含み損：上昇圧力が強い = 反転失敗
        has_buy_pressure = ofi > 0.2 or depth_imb > 0.15
        if micro_bias > 0.2 and has_buy_pressure:
            return True
        return ofi > 0.15 and depth_imb > 0.15

def merge_nearby_levels(levels: List[Dict], tolerance: float = 0.005) -> List[Dict]:
    """
    近い価格帯のレベルを統合し、strengthを加算
    
    Args:
        levels: レベルのリスト
        tolerance: 統合する価格の許容範囲（例: 0.005 = 0.5%）
    
    Returns:
        統合されたレベルのリスト
    """
    if not levels:
        return []
    
    # 価格でソート
    sorted_levels = sorted(levels, key=lambda x: x["level_now"])
    
    merged = []
    current_group = [sorted_levels[0]]
    
    for lv in sorted_levels[1:]:
        last_price = current_group[-1]["level_now"]
        current_price = lv["level_now"]
        
        # 価格が近い場合（tolerance以内）は同じグループに
        if abs(current_price - last_price) / last_price <= tolerance:
            current_group.append(lv)
        else:
            # グループを統合
            merged.append(merge_level_group(current_group))
            current_group = [lv]
    
    # 最後のグループを統合
    if current_group:
        merged.append(merge_level_group(current_group))
    
    return merged

def merge_level_group(group: List[Dict]) -> Dict:
    """
    同じ価格帯のレベルを1つに統合
    """
    if len(group) == 1:
        group[0]["merged_count"] = 1
        return group[0]
    
    # 加重平均で価格を計算（strengthで重み付け）
    total_strength = sum(lv.get("strength", 1.0) for lv in group)
    weighted_price = sum(lv["level_now"] * lv.get("strength", 1.0) for lv in group) / total_strength
    
    # strengthを加算（上限2.0）
    combined_strength = min(2.0, total_strength)
    
    # ソース情報を結合
    sources = [lv.get("metadata", {}).get("source", "unknown") for lv in group]
    source_counts = {}
    for src in sources:
        source_counts[src] = source_counts.get(src, 0) + 1
    
    merged = {
        "level_now": weighted_price,
        "kind": group[0].get("kind", "support"),
        "symbol": group[0].get("symbol", ""),
        "strength": combined_strength,
        "merged_count": len(group),
        "metadata": {
            "source": "merged",
            "sources": source_counts,
            "original_prices": [lv["level_now"] for lv in group]
        }
    }
    
    return merged

def check_reversal_signal(row: pd.Series, direction: str, 
                          micro_bias_col: str, ofi_col: str, 
                          qi_col: str, depth_col: str) -> bool:
    """
    反転シグナルのチェック
    direction: 'buy'（下から戻り）or 'sell'（上から戻り）
    """
    conditions = []
    
    # micro_bias: 買いなら正、売りなら負
    if micro_bias_col in row.index and not pd.isna(row[micro_bias_col]):
        if direction == "buy" and row[micro_bias_col] > 0:
            conditions.append(True)
        elif direction == "sell" and row[micro_bias_col] < 0:
            conditions.append(True)
    
    # OFI: 買いなら正、売りなら負
    if ofi_col in row.index and not pd.isna(row[ofi_col]):
        if direction == "buy" and row[ofi_col] > 0:
            conditions.append(True)
        elif direction == "sell" and row[ofi_col] < 0:
            conditions.append(True)
    
    # QI: 買いなら正、売りなら負
    if qi_col in row.index and not pd.isna(row[qi_col]):
        if direction == "buy" and row[qi_col] > 0:
            conditions.append(True)
        elif direction == "sell" and row[qi_col] < 0:
            conditions.append(True)
    
    # depth_imb: 買いなら正、売りなら負
    if depth_col in row.index and not pd.isna(row[depth_col]):
        if direction == "buy" and row[depth_col] > 0:
            conditions.append(True)
        elif direction == "sell" and row[depth_col] < 0:
            conditions.append(True)
    
    # いずれか1つ以上満たせばTrue
    return len(conditions) > 0 and any(conditions)

def run_backtest(lob_df: pd.DataFrame, levels: List[Dict], 
                 k_tick: float = 5.0, x_tick: float = 10.0, y_tick: float = 5.0,
                 max_hold_bars: int = 60, strength_threshold: float = 0.5,
                 roll_n: int = 20, k_depth: int = 5) -> pd.DataFrame:
    """
    銘柄別逆張りバックテスト
    """
    # 強度閾値でフィルタ
    valid_levels = [lv for lv in levels if lv.get("strength", 0) >= strength_threshold]
    
    all_trades = []
    
    # 銘柄別に処理
    if "symbol" in lob_df.columns:
        symbols = lob_df["symbol"].unique()
        print(f"Backtesting {len(symbols)} symbols...", flush=True)
        
        for sym in symbols:
            # 銘柄データとレベルを抽出
            sym_df = lob_df[lob_df["symbol"] == sym].copy().reset_index(drop=True)
            sym_levels = [lv for lv in valid_levels if lv.get("symbol", "") == str(sym)]
            
            if len(sym_levels) == 0:
                print(f"  {sym}: No valid levels, skipping", flush=True)
                continue
            
            # 銘柄ごとにバックテスト
            sym_trades = run_backtest_single_symbol(
                sym_df, sym_levels, str(sym), k_tick, x_tick, y_tick,
                max_hold_bars, roll_n, k_depth
            )
            all_trades.extend(sym_trades)
            print(f"  {sym}: {len(sym_trades)} trades", flush=True)
    else:
        # 銘柄列がない場合は全体で処理
        all_trades = run_backtest_single_symbol(
            lob_df, valid_levels, "", k_tick, x_tick, y_tick,
            max_hold_bars, roll_n, k_depth
        )
    
    return pd.DataFrame(all_trades)

def run_backtest_single_symbol(lob_df: pd.DataFrame, levels: List[Dict],
                                symbol: str, k_tick: float, x_tick: float, y_tick: float,
                                max_hold_bars: int, roll_n: int, k_depth: int) -> List[Dict]:
    """
    単一銘柄のバックテスト
    
    売買時間:
    - 前場: 9:00 - 11:30
    - 後場: 12:30 - 15:15
    セッションをまたぐトレードは禁止、各セッション終了時に強制決済
    """
    # レベルを統合：近い価格帯（±0.5%以内）を1つにまとめ、strengthを加算
    merged_levels = merge_nearby_levels(levels, tolerance=0.005)
    
    micro_bias_col = "micro_bias"
    ofi_col = f"ofi_{roll_n}"
    qi_col = "qi_l1"
    depth_col = f"depth_imb_{k_depth}"
    
    trades = []
    position = None
    current_session = None
    
    for i, row in lob_df.iterrows():
        price = row["mid"]
        current_time = row["ts"]
        
        # セッション判定
        session = get_trading_session(current_time)
        session_changed = (current_session is not None and session != current_session)
        current_session = session
        
        # ポジション保有中の処理
        if position is not None:
            hold_bars = i - position["entry_idx"]
            pnl_tick = 0.0
            exit_reason = ""
            
            # 現在の損益を計算
            if position["direction"] == "buy":
                pnl_tick = price - position["entry_price"]
            else:
                pnl_tick = position["entry_price"] - price
            
            # セッションが変わったら強制決済
            if session_changed or session == 'closed':
                exit_reason = "SESSION_END"
            
            # 動的利確ロジック
            elif pnl_tick > 0:  # 含み益がある場合のみ
                # 1. 半値戻しでの利確チェック
                has_drop, high_price, low_price, drop_size = detect_recent_drop(lob_df, i, lookback=10)
                if has_drop and position["direction"] == "buy":
                    # 急落からの反発：半値戻し（50%）到達で利確（引き上げ：5 tick）
                    half_retracement = low_price + (drop_size * 0.5)
                    if price >= half_retracement and pnl_tick >= 5.0:  # 最低5tick以上の利益
                        exit_reason = "HALF_RETRACE"
                
                # 2. 次のレジスタンスレベル接近での利確
                if not exit_reason:
                    next_resistance = find_next_resistance(price, position["direction"], merged_levels)
                    if next_resistance is not None:
                        distance_to_resistance = abs(price - next_resistance)
                        # レジスタンスまで1.5tick以内で、かつ十分な利益がある場合（引き上げ：8 tick）
                        if distance_to_resistance <= 1.5 and pnl_tick >= 8.0:
                            exit_reason = "NEAR_RESISTANCE"
                
                # 3. 反発が弱まっている場合の早期利確
                if not exit_reason and hold_bars >= 5:
                    if is_reversal_weakening(row, position["direction"], ofi_col, depth_col):
                        # 反発が弱まっており、かつ十分な利益がある場合（引き上げ：5 tick）
                        if pnl_tick >= 5.0:
                            exit_reason = "WEAK_REVERSAL"
            
            # 早期損切りロジック（含み損時）
            elif pnl_tick < 0 and hold_bars >= 2:  # 2本以上保有で含み損
                # 反転シグナルが消失し、逆方向の圧力が強い場合は早期損切り
                if is_reversal_failing(row, position["direction"], micro_bias_col, ofi_col, depth_col):
                    # 含み損が-1.5 tick以上で、かつy_tick到達前なら早期損切り
                    if pnl_tick >= -y_tick and pnl_tick <= -1.5:
                        exit_reason = "EARLY_SL"
            
            # 通常の利確・損切ロジック
            if not exit_reason:
                if pnl_tick >= x_tick:
                    exit_reason = "TP"
                elif pnl_tick <= -y_tick:
                    exit_reason = "SL"
                elif hold_bars >= max_hold_bars:
                    exit_reason = "TO"
            
            if exit_reason:
                trades.append({
                    "entry_ts": position["entry_ts"],
                    "exit_ts": row["ts"],
                    "symbol": symbol,
                    "direction": position["direction"],
                    "entry_price": position["entry_price"],
                    "exit_price": price,
                    "pnl_tick": pnl_tick,
                    "hold_bars": hold_bars,
                    "exit_reason": exit_reason,
                    "level": position["level"]
                })
                position = None
        
        # 新規エントリー判定（取引セッション内のみ、セッション終了間近は除外）
        can_enter = (session in ['morning', 'afternoon'] and 
                    not is_session_end_approaching(current_time, session, minutes_before=5))
        
        if position is None and can_enter:
            for lv in merged_levels:
                level_price = lv["level_now"]
                level_strength = lv.get("strength", 1.0)
                level_count = lv.get("merged_count", 1)  # 統合されたレベル数
                
                # 買い逆張り（レベル付近で下から反発）
                if is_near_level(price, level_price, k_tick):
                    if price <= level_price + k_tick:
                        if check_reversal_signal(row, "buy", micro_bias_col, ofi_col, qi_col, depth_col):
                            position = {
                                "entry_idx": i,
                                "entry_price": price,
                                "direction": "buy",
                                "level": level_price,
                                "level_strength": level_strength,
                                "level_count": level_count,
                                "entry_ts": row["ts"]
                            }
                            break
                    
                    # 売り逆張り（レベル付近で上から反落）
                    if price >= level_price - k_tick:
                        if check_reversal_signal(row, "sell", micro_bias_col, ofi_col, qi_col, depth_col):
                            position = {
                                "entry_idx": i,
                                "entry_price": price,
                                "direction": "sell",
                                "level": level_price,
                                "level_strength": level_strength,
                                "level_count": level_count,
                                "entry_ts": row["ts"]
                            }
                            break
    
    # ループ終了時に持ち越しポジションを強制精算
    if position is not None:
        last_price = lob_df.iloc[-1]["mid"]
        last_ts = lob_df.iloc[-1]["ts"]
        if position["direction"] == "buy":
            pnl_tick = last_price - position["entry_price"]
        else:
            pnl_tick = position["entry_price"] - last_price
        
        trades.append({
            "entry_ts": position["entry_ts"],
            "exit_ts": last_ts,
            "symbol": symbol,
            "direction": position["direction"],
            "entry_price": position["entry_price"],
            "exit_price": last_price,
            "pnl_tick": pnl_tick,
            "hold_bars": len(lob_df) - 1 - position["entry_idx"],
            "exit_reason": "EOD",
            "level": position["level"]
        })
    
    return trades

def calculate_metrics(trades_df: pd.DataFrame) -> Dict[str, Any]:
    """評価指標の計算"""
    if len(trades_df) == 0:
        return {"total_trades": 0}
    
    total = len(trades_df)
    wins = len(trades_df[trades_df["pnl_tick"] > 0])
    losses = len(trades_df[trades_df["pnl_tick"] < 0])
    win_rate = wins / total if total > 0 else 0.0
    
    avg_pnl = trades_df["pnl_tick"].mean()
    total_pnl = trades_df["pnl_tick"].sum()
    
    # 最大ドローダウン（簡易）
    cumsum = trades_df["pnl_tick"].cumsum()
    running_max = cumsum.expanding().max()
    dd = (cumsum - running_max).min()
    
    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "avg_pnl_tick": avg_pnl,
        "total_pnl_tick": total_pnl,
        "max_dd_tick": dd,
        "avg_hold_bars": trades_df["hold_bars"].mean() if total > 0 else 0
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lob-features", required=True, help="LOB features CSV")
    ap.add_argument("--levels", required=True, help="S/R levels JSONL")
    ap.add_argument("--out-trades", required=True, help="output trades CSV")
    ap.add_argument("--out-summary", required=True, help="output summary JSON")
    # config.pyから取得（オプション指定があれば優先）
    defaults = config.DEFAULT_PARAMS
    ap.add_argument("--k-tick", type=float, default=defaults["k_tick"], help="reaction band width")
    ap.add_argument("--x-tick", type=float, default=defaults["x_tick"], help="take profit")
    ap.add_argument("--y-tick", type=float, default=defaults["y_tick"], help="stop loss")
    ap.add_argument("--max-hold-bars", type=int, default=defaults["max_hold_bars"], help="timeout bars")
    ap.add_argument("--strength-threshold", type=float, default=defaults["strength_th"])
    ap.add_argument("--roll-n", type=int, default=defaults["roll_n"])
    ap.add_argument("--k-depth", type=int, default=defaults["k_depth"])
    args = ap.parse_args()
    
    try:
        # 出力ディレクトリ確保
        validation.ensure_output_directory(args.out_trades)
        validation.ensure_output_directory(args.out_summary)
        
        lob_df = load_lob_features(args.lob_features)
        levels = load_levels(args.levels)
        
        # 除外銘柄をフィルタ
        if "symbol" in lob_df.columns:
            all_symbols = lob_df["symbol"].unique()
            active_symbols = config.list_active_symbols(all_symbols)
            excluded = set(all_symbols) - set(active_symbols)
            if excluded:
                logger.info(f"Excluding symbols: {excluded}")
                lob_df = lob_df[lob_df["symbol"].isin(active_symbols)].copy()
                levels = [lv for lv in levels if lv.get("symbol") not in excluded]
        
        trades_df = run_backtest(
            lob_df, levels,
            k_tick=args.k_tick,
            x_tick=args.x_tick,
            y_tick=args.y_tick,
            max_hold_bars=args.max_hold_bars,
            strength_threshold=args.strength_threshold,
            roll_n=args.roll_n,
            k_depth=args.k_depth
        )
        
        trades_df.to_csv(args.out_trades, index=False)
        logger.info(f"Wrote: {args.out_trades} trades={len(trades_df)}")
        
        metrics = calculate_metrics(trades_df)
        with open(args.out_summary, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        logger.info(f"Wrote: {args.out_summary}")
        print("Backtest Metrics:", json.dumps(metrics, indent=2))
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(2)

if __name__ == "__main__":
    main()
