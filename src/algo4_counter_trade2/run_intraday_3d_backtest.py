#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
過去5営業日の分足揉み合いゾーンを優先的に使用するバックテスト
レベルが不足する場合は日足のVPOC/S/Rを補完
"""
import subprocess
import sys
import os
import pandas as pd
import json
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd: list):
    """コマンド実行"""
    # デバッグ出力
    for i, item in enumerate(cmd):
        if not isinstance(item, str):
            print(f"ERROR: cmd[{i}] is {type(item)}: {item}")
            raise TypeError(f"All cmd items must be str, but cmd[{i}] is {type(item)}")
    
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        print(f"ERROR: Command failed with code {result.returncode}")
        sys.exit(1)

def generate_intraday_only_levels(trade_date, ohlc_path, chart_dir, lookback_days=3,
                                 level_weights=None):
    """
    過去N営業日の分足揉み合いゾーンのみを生成
    
    Args:
        trade_date: 取引日（datetime.date）
        ohlc_path: OHLCデータパス
        chart_dir: チャートデータディレクトリ
        lookback_days: 遡る営業日数
        level_weights: レベルタイプ別の重み係数
                      {'intraday': 2.0, 'daily': 1.0, 'sr': 0.8, 'psych': 0.6}
                      0.0で除外
    
    Returns:
        levels_path: 生成されたレベルファイルパス
    """
    # デフォルトの重み係数
    if level_weights is None:
        level_weights = {
            'intraday': 2.0,    # 分足揉み合い（最優先）
            'daily': 1.0,        # 日足揉み合い
            'sr': 0.8,           # サポート・レジスタンスライン
            'psych': 0.6         # 心理的節目
        }
    
    import glob
    
    # 分足データから実際の営業日を取得
    pattern = os.path.join(chart_dir, "stock_chart_3M_*_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # 1つ目のファイルから日付を取得
    df = pd.read_csv(files[0], encoding='utf-8-sig')
    if '日付' not in df.columns:
        return None
    
    df['日付'] = pd.to_datetime(df['日付'])
    all_dates = sorted(df['日付'].dt.date.unique())
    
    # 取引日より前の営業日を抽出
    past_dates = [d for d in all_dates if d < trade_date]
    
    if len(past_dates) < lookback_days:
        print(f"  警告: 過去{lookback_days}営業日のデータが不足（{len(past_dates)}日のみ）")
        target_dates = past_dates
    else:
        target_dates = past_dates[-lookback_days:]
    
    print(f"  対象営業日: {target_dates}")
    
    # 分足揉み合いゾーンのみを生成するスクリプトを作成
    levels_path = f"output/levels_intraday5d_{trade_date.strftime('%Y%m%d')}.jsonl"
    
    # sr_levels.pyを使わずに直接揉み合いゾーンを生成
    from sr_levels import find_consolidation_from_intraday_chart, read_ohlc
    
    all_levels = []
    
    # OHLCから銘柄リストを取得
    ohlc_df = read_ohlc(ohlc_path)
    if "symbol" in ohlc_df.columns:
        symbols = ohlc_df["symbol"].unique()
    else:
        symbols = [None]
    
    for sym in symbols:
        if sym is None or pd.isna(sym):
            continue
        
        # 銘柄コードを正規化（5016.0 → 5016 or 215A → 215A）
        sym_str = str(sym)
        if '.' in sym_str:
            sym_code = sym_str.split('.')[0]
        else:
            sym_code = sym_str
        
        # 分足データを読み込み
        pattern = os.path.join(chart_dir, f"stock_chart_3M_{sym_code}_*.csv")
        files = glob.glob(pattern)
        
        if not files:
            print(f"  [{sym}] 分足データが見つかりません: {pattern}")
            continue
        
        df_3m = pd.read_csv(files[0], encoding='utf-8-sig')
        if '日付' not in df_3m.columns:
            continue
        
        df_3m['日付'] = pd.to_datetime(df_3m['日付'])
        
        # 対象日のデータのみフィルタ
        df_filtered = df_3m[df_3m['日付'].dt.date.isin(target_dates)].copy()
        
        if df_filtered.empty:
            continue
        
        print(f"  [{sym}] 分足: {len(df_3m)}行 → {len(df_filtered)}行（{target_dates[0]}～{target_dates[-1]}のみ）")
        
        # 日別に揉み合いゾーンを検出
        if '時刻' in df_filtered.columns:
            df_filtered['datetime'] = pd.to_datetime(df_filtered['日付'].astype(str) + ' ' + df_filtered['時刻'], format='%Y-%m-%d %H:%M', errors='coerce')
        else:
            df_filtered['datetime'] = df_filtered['日付']
        
        df_filtered['date'] = df_filtered['datetime'].dt.date
        
        for date_val in sorted(df_filtered['date'].unique()):
            df_day = df_filtered[df_filtered['date'] == date_val]
            
            # 価格帯別出来高を計算
            volume_profile = {}
            bin_size = 0.5
            
            for _, row in df_day.iterrows():
                high = row.get('高値')
                low = row.get('安値')
                volume = row.get('出来高', 0)
                
                if pd.isna(high) or pd.isna(low) or pd.isna(volume):
                    continue
                
                price_range = [low + i * bin_size for i in range(int((high - low) / bin_size) + 1)]
                for price in price_range:
                    bin_key = int(price / bin_size) * bin_size
                    volume_profile[bin_key] = volume_profile.get(bin_key, 0) + volume
            
            if not volume_profile:
                continue
            
            # 高出来高ゾーンを検出
            volumes = list(volume_profile.values())
            threshold = pd.Series(volumes).quantile(0.70)
            
            sorted_bins = sorted(volume_profile.items())
            
            zones = []
            current_zone = []
            
            for price, vol in sorted_bins:
                if vol >= threshold:
                    current_zone.append((price, vol))
                else:
                    if len(current_zone) >= 3:
                        zones.append(current_zone)
                    current_zone = []
            
            if len(current_zone) >= 3:
                zones.append(current_zone)
            
            # レベルとして追加
            for zone in zones:
                prices = [p for p, v in zone]
                volumes = [v for p, v in zone]
                
                zone_start = min(prices)
                zone_end = max(prices) + bin_size
                zone_center = (zone_start + zone_end) / 2
                total_volume = sum(volumes)
                max_volume = max(volumes) if volumes else 1.0
                
                # 分足揉み合いは設定された係数でブースト（上限1.0）
                base_strength = (total_volume / max_volume) if max_volume > 0 else 0.5
                strength = min(base_strength * level_weights['intraday'], 1.0)
                
                all_levels.append({
                    "level_now": float(zone_center),
                    "type": f"intraday_consolidation_{date_val}",
                    "kind": "support",  # 必須フィールド
                    "symbol": str(sym),
                    "strength": float(strength),
                    "metadata": {
                        "date": str(date_val),
                        "zone_start": float(zone_start),
                        "zone_end": float(zone_end),
                        "zone_width": float(zone_end - zone_start),
                        "volume": float(total_volume),
                        "source": "3min_recent_3days"
                    }
                })
    
    # 日足のVPOC/S/Rを補完
    print(f"\n  日足S/Rを補完...")
    from sr_levels import (find_consolidation_from_daily_chart, 
                          find_psychological_levels,
                          find_support_resistance_lines)
    
    # 価格範囲を計算（心理的節目用）
    price_min = float('inf')
    price_max = float('-inf')
    
    for sym in symbols:
        if sym is None or pd.isna(sym):
            continue
        
        sym_str = str(sym)
        if '.' in sym_str:
            sym_code = sym_str.split('.')[0]
        else:
            sym_code = sym_str
        
        # 日足揉み合いゾーン（前日まで）- 重みが0でなければ生成
        if level_weights['daily'] > 0:
            daily_levels = find_consolidation_from_daily_chart(
                chart_dir, sym_code, bin_size=1.0,
                exclude_date_after=trade_date.strftime('%Y-%m-%d')
            )
            
            for lv in daily_levels:
                if 'metadata' not in lv:
                    lv['metadata'] = {}
                lv['metadata']['source'] = 'daily_consolidation'
                lv['symbol'] = str(sym)
                # 日足揉み合いの重み係数を適用
                lv['strength'] = min(1.0, lv.get('strength', 0.5) * level_weights['daily'])
            
            all_levels.extend(daily_levels)
        
        # 通常のサポート・レジスタンスライン（日足から）- 重みが0でなければ生成
        if level_weights['sr'] > 0:
            pattern = os.path.join(chart_dir, f"stock_chart_D_{sym_code}_*.csv")
            files = glob.glob(pattern)
            
            if files:
                df_daily = pd.read_csv(files[0], encoding='utf-8-sig')
                if '日付' in df_daily.columns:
                    df_daily['日付'] = pd.to_datetime(df_daily['日付'])
                    # 過去20営業日のデータ（dateオブジェクトと比較するためdatetimeに変換）
                    trade_date_dt = pd.to_datetime(trade_date)
                    df_daily_filtered = df_daily[df_daily['日付'] < trade_date_dt]
                    if len(df_daily_filtered) > 20:
                        df_daily_filtered = df_daily_filtered.tail(20)
                    
                    if len(df_daily_filtered) > 0:
                        sr_levels = find_support_resistance_lines(
                            df_daily_filtered, symbol=str(sym), 
                            lookback_days=20, prominence=0.02
                        )
                        
                        for lv in sr_levels:
                            if 'metadata' not in lv:
                                lv['metadata'] = {}
                            lv['metadata']['source'] = 'support_resistance'
                            # レジサポの重み係数を適用
                            lv['strength'] = min(1.0, lv.get('strength', 0.5) * level_weights['sr'])
                        
                        all_levels.extend(sr_levels)
                        
                        # 価格範囲を更新
                        if '高値' in df_daily_filtered.columns and '安値' in df_daily_filtered.columns:
                            price_min = min(price_min, df_daily_filtered['安値'].min())
                            price_max = max(price_max, df_daily_filtered['高値'].max())
    
    # 心理的節目（全銘柄共通）- 重みが0でなければ生成
    if level_weights['psych'] > 0 and price_min != float('inf') and price_max != float('-inf'):
        psych_levels = find_psychological_levels(
            price_min, price_max, symbol="",
            round_levels=[100, 50, 10]
        )
        
        for lv in psych_levels:
            if 'metadata' not in lv:
                lv['metadata'] = {}
            lv['metadata']['source'] = 'psychological'
            # 心理的節目の重み係数を適用
            lv['strength'] = min(1.0, lv.get('strength', 0.3) * level_weights['psych'])
        
        all_levels.extend(psych_levels)
    
    # ファイルに保存
    output_path = f"output/levels_intraday5d_{trade_date.strftime('%Y%m%d')}.jsonl"
    os.makedirs("output", exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for lv in all_levels:
            f.write(json.dumps(lv, ensure_ascii=False) + '\n')
    
    return output_path


def main():
    # ========== 設定 ==========
    LOOKBACK_DAYS = 3  # 過去何営業日の分足揉み合いを使用するか
    
    print(f"=== 過去{LOOKBACK_DAYS}営業日分足揉み合いバックテスト ===\n")
    
    # レベルタイプ別の重み係数（0.0で除外）
    level_weights = {
        'intraday': 2.0,    # 分足揉み合い（最優先）
        'daily': 0.0,        # 日足揉み合い（除外）
        'sr': 0.0,           # サポート・レジスタンスライン（除外）
        'psych': 0.0         # 心理的節目（除外）
    }
    
    print("レベルタイプ別重み係数:")
    for level_type, weight in level_weights.items():
        status = "有効" if weight > 0 else "無効"
        print(f"  - {level_type}: {weight} ({status})")
    print()
    
    # Step 0: マーケットデータ結合
    print("Step 0: マーケットデータ結合")
    run_cmd([
        sys.executable, "merge_market_data.py",
        "--input-dir", "input/market_order_book",
        "--output", "input/rss_market_data_merged.csv"
    ])
    
    # Step 0.5: LOB特徴量とOHLC生成
    print("\nStep 0.5: LOB特徴量 & OHLC生成")
    run_cmd([
        sys.executable, "lob_features.py",
        "--rss", "input/rss_market_data_merged.csv",
        "--out", "output/lob_features.csv"
    ])
    run_cmd([
        sys.executable, "ohlc_from_rss.py",
        "--rss", "input/rss_market_data_merged.csv",
        "--out", "output/ohlc_1min.csv",
        "--freq", "1min"
    ])
    
    # Step 1: チャートデータをインポート
    print("\nStep 1: チャートデータインポート")
    run_cmd([sys.executable, "import_chart_data.py"])
    
    # LOBデータから取引日を抽出
    lob_df = pd.read_csv("output/lob_features.csv")
    lob_df['ts'] = pd.to_datetime(lob_df['ts'])
    lob_df['date'] = lob_df['ts'].dt.date
    trading_dates = sorted(lob_df['date'].unique())
    
    print(f"\n検出された取引日: {len(trading_dates)}日")
    for td in trading_dates:
        print(f"  - {td}")
    
    all_trades = []
    
    # 日別にレベル生成 & バックテスト
    for i, trade_date in enumerate(trading_dates):
        print(f"\n{'='*60}")
        print(f"取引日 {i+1}/{len(trading_dates)}: {trade_date}")
        print(f"{'='*60}")
        
        # 過去N営業日の分足揉み合いゾーンを生成
        levels_path = generate_intraday_only_levels(
            trade_date, "output/ohlc_1min.csv", "input/chart_data", 
            lookback_days=LOOKBACK_DAYS, level_weights=level_weights
        )
        
        if levels_path is None:
            print("  レベル生成失敗、スキップ")
            continue
        
        # その日のバックテスト実行
        trades_path = f"output/trades_5d_{trade_date.strftime('%Y%m%d')}.csv"
        summary_path = f"output/backtest_5d_{trade_date.strftime('%Y%m%d')}.json"
        print(f"\nバックテスト実行（{trade_date}）")
        
        # その日のLOBデータのみ抽出
        lob_day_path = f"output/lob_features_5d_{trade_date.strftime('%Y%m%d')}.csv"
        lob_day = lob_df[lob_df['date'] == trade_date].copy()
        lob_day.to_csv(lob_day_path, index=False)
        print(f"  LOBデータ: {len(lob_day)}行")
        
        run_cmd([
            sys.executable, "backtest_mean_reversion.py",
            "--lob-features", lob_day_path,
            "--levels", levels_path,
            "--out-trades", trades_path,
            "--out-summary", summary_path
        ])
        
        # トレード結果を集約
        if os.path.exists(trades_path):
            df_trades = pd.read_csv(trades_path)
            if not df_trades.empty:
                all_trades.append(df_trades)
                print(f"  トレード数: {len(df_trades)}件")
    
    # 全日のトレードを結合
    if all_trades:
        print(f"\n{'='*60}")
        print("全期間の結果を統合")
        print(f"{'='*60}")
        
        combined_trades = pd.concat(all_trades, ignore_index=True)
        combined_trades.to_csv("output/trades_5d_combined.csv", index=False)
        
        # サマリー計算
        total = len(combined_trades)
        wins = len(combined_trades[combined_trades["pnl_tick"] > 0])
        losses = len(combined_trades[combined_trades["pnl_tick"] < 0])
        win_rate = wins / total if total > 0 else 0.0
        avg_pnl = combined_trades["pnl_tick"].mean()
        total_pnl = combined_trades["pnl_tick"].sum()
        
        summary = {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "avg_pnl_tick": avg_pnl,
            "total_pnl_tick": total_pnl,
            "trading_dates": len(trading_dates)
        }
        
        with open("output/backtest_5d_combined.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n=== 統合結果 ===")
        print(f"取引日数: {len(trading_dates)}日")
        print(f"総トレード数: {total}件")
        print(f"勝ち: {wins}件 / 負け: {losses}件")
        print(f"勝率: {win_rate*100:.1f}%")
        print(f"平均損益: {avg_pnl:.2f} tick")
        print(f"総損益: {total_pnl:.2f} tick")
        print(f"\n保存先:")
        print(f"  - output/trades_5d_combined.csv")
        print(f"  - output/backtest_5d_combined.json")
    else:
        print("\nトレードがありませんでした。")

if __name__ == "__main__":
    main()
