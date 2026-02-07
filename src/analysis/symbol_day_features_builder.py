import numpy as np
import pandas as pd

# --- LOB特徴量計算関数 ---
def compute_lob_features_from_raw(md: pd.DataFrame, roll_n: int = 20, k_depth: int = 5) -> pd.DataFrame:
    """
    生板データ(md)から、micro_bias / ofi_{roll_n} / depth_imb_{k_depth} を計算して返す。
    md は timestamp で昇順ソート済みが望ましい。
    必須列: bid{i}_price, bid{i}_size, ask{i}_price, ask{i}_size (i=1..k_depth)
    """
    df = md.copy()
    req = []
    for i in range(1, k_depth + 1):
        req += [f"bid{i}_price", f"bid{i}_size", f"ask{i}_price", f"ask{i}_size"]
    missing = [c for c in req if c not in df.columns]
    if missing:
        df["mid"] = np.nan
        df["micro_bias"] = np.nan
        df[f"ofi_{roll_n}"] = np.nan
        df[f"depth_imb_{k_depth}"] = np.nan
        return df
    for c in req:
        if c in df.columns:
            col = df[c]
            # DataFrame型なら1列目を使う
            if isinstance(col, pd.DataFrame):
                col = col.iloc[:, 0]
            if isinstance(col, pd.Series):
                df[c] = pd.to_numeric(col, errors="coerce")
    # Series型でなければ1列目を使う
    def get_col_safe(df, col):
        if col in df.columns:
            v = df[col]
            if isinstance(v, pd.DataFrame):
                return v.iloc[:, 0]
            return v
        return pd.Series([np.nan]*len(df), index=df.index)
    bid1_px = get_col_safe(df, "bid1_price")
    ask1_px = get_col_safe(df, "ask1_price")
    bid1_sz = get_col_safe(df, "bid1_size")
    ask1_sz = get_col_safe(df, "ask1_size")
    df["mid"] = (ask1_px + bid1_px) / 2.0
    spread = (ask1_px - bid1_px).replace(0, np.nan)
    denom = (bid1_sz + ask1_sz).replace(0, np.nan)
    micro_price = (ask1_px * bid1_sz + bid1_px * ask1_sz) / denom
    df["micro_bias"] = (micro_price - df["mid"]) / spread
    bid_depth = None
    ask_depth = None
    for i in range(1, k_depth + 1):
        b = df[f"bid{i}_size"]
        a = df[f"ask{i}_size"]
        bid_depth = b if bid_depth is None else (bid_depth + b)
        ask_depth = a if ask_depth is None else (ask_depth + a)
    depth_denom = (bid_depth + ask_depth).replace(0, np.nan)
    df[f"depth_imb_{k_depth}"] = (bid_depth - ask_depth) / depth_denom
    d_bid_px = bid1_px.diff()
    d_ask_px = ask1_px.diff()
    d_bid_sz = bid1_sz.diff()
    d_ask_sz = ask1_sz.diff()
    bid_contrib = np.where(d_bid_px > 0, bid1_sz, np.where(d_bid_px == 0, d_bid_sz, 0.0))
    ask_contrib = np.where(d_ask_px < 0, -ask1_sz, np.where(d_ask_px == 0, -d_ask_sz, 0.0))
    ofi_1 = pd.Series(bid_contrib, index=df.index).fillna(0.0) + pd.Series(ask_contrib, index=df.index).fillna(0.0)
    df[f"ofi_{roll_n}"] = ofi_1.rolling(roll_n, min_periods=roll_n).sum()
    return df
"""
symbol_day_features テーブル生成モジュール
設計書に基づき、(symbol, trade_date)単位の環境特徴量を構築
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

def build_symbol_day_features(
    trades_df: pd.DataFrame,
    chart_data: Dict[str, pd.DataFrame],
    market_data: Dict[str, pd.DataFrame],
    levels: Dict[str, List[Dict]],
    business_days: List[datetime],
    symbols: List[str]
) -> pd.DataFrame:
    """
    (symbol, trade_date)単位の環境特徴量テーブルを生成
    Args:
        trades_df: バックテスト結果
        chart_data: {symbol: DataFrame(日足・分足)}
        market_data: {symbol: DataFrame(当日板データ)}
        levels: {symbol: [level_dict, ...]} (当日有効レベル)
        business_days: 対象営業日リスト
        symbols: 対象銘柄リスト
    Returns:
        symbol_day_features: DataFrame
    """
    # chart_data: 日本語カラム対応・timestamp列生成
    chart_data_fixed = {}
    for symbol, df in chart_data.items():
        if '日付' in df.columns and '時刻' in df.columns:
            ts = pd.to_datetime(df['日付'].astype(str) + ' ' + df['時刻'].astype(str), errors='coerce')
            df = df.copy()
            df['timestamp'] = ts
            # 英語カラム名に変換
            rename_map = {'始値': 'open', '高値': 'high', '安値': 'low', '終値': 'close', '出来高': 'volume', '銘柄コード': 'symbol'}
            for jp, en in rename_map.items():
                if jp in df.columns:
                    df[en] = df[jp]
            chart_data_fixed[symbol] = df
        else:
            chart_data_fixed[symbol] = df
    # market_data: 日本語カラム対応・timestamp/symbol列生成
    market_data_fixed = {}
    for symbol, df in market_data.items():
        if '記録日時' in df.columns and '銘柄コード' in df.columns:
            df = df.copy()
            df['timestamp'] = pd.to_datetime(df['記録日時'], errors='coerce')
            df['symbol'] = df['銘柄コード'].astype(str)
            # --- 板カラム名の正規化 ---
            # --- 重複なしrename_map（1本目はsuffix無し、2本目以降はi=2..10） ---
            rename_map = {
                '最良買気配値': 'bid1_price',
                '最良買気配数量': 'bid1_size',
                '最良売気配値': 'ask1_price',
                '最良売気配数量': 'ask1_size',
            }
            for i in range(2, 11):
                rename_map[f'最良買気配値{i}'] = f'bid{i}_price'
                rename_map[f'最良買気配数量{i}'] = f'bid{i}_size'
                rename_map[f'最良売気配値{i}'] = f'ask{i}_price'
                rename_map[f'最良売気配数量{i}'] = f'ask{i}_size'
            df = df.rename(columns=rename_map)
            # --- 重複カラムを削除（最初の出現のみ残す） ---
            df = df.loc[:, ~df.columns.duplicated()]
            market_data_fixed[symbol] = df
        else:
            market_data_fixed[symbol] = df
    records = []
    for i, trade_date in enumerate(business_days):
        # 営業日ベースで前日を取得
        prev_date = business_days[i-1] if i > 0 else None
        for symbol in symbols:
            rec = {
                'symbol': symbol,
                'trade_date': trade_date.strftime('%Y-%m-%d'),
            }
            # --- chartデータ: 全期間/過去/当日 ---
            df_all = chart_data_fixed.get(symbol)
            if df_all is not None:
                df_all = df_all.sort_values('timestamp')
                df_past = df_all[df_all['timestamp'] < trade_date]
                df_today = df_all[df_all['timestamp'].dt.date == trade_date.date()]
                if prev_date is not None:
                    prev_day = df_past[df_past['timestamp'].dt.date == prev_date.date()]
                else:
                    prev_day = pd.DataFrame()
                # 出来高
                rec['prev_day_volume'] = prev_day['volume'].sum() if not prev_day.empty else np.nan
                # 20日平均出来高（日次集約）
                daily_vol = df_past.copy()
                daily_vol['date'] = daily_vol['timestamp'].dt.date
                daily_vol = daily_vol.groupby('date')['volume'].sum()
                mean_20d = daily_vol.tail(20).mean() if not daily_vol.empty else np.nan
                rec['prev_day_volume_ratio_20d'] = rec['prev_day_volume'] / mean_20d if mean_20d and not np.isnan(mean_20d) else np.nan
                # ATR計算用: df_pastから日次OHLC
                past = df_past.copy()
                past['date'] = past['timestamp'].dt.date
                daily_ohlc = past.groupby('date').agg(
                    high=('high','max'),
                    low=('low','min'),
                    close=('close','last'),
                ).reset_index()
                last_20d_daily = daily_ohlc.tail(20)
                # 前日リターン
                if not prev_day.empty:
                    o = prev_day.iloc[0]['open']
                    c = prev_day.iloc[-1]['close']
                    rec['prev_day_return'] = (c - o) / o if o else np.nan
                    h = prev_day['high'].max()
                    l = prev_day['low'].min()
                    rec['prev_day_range_pct'] = (h - l) / c if c else np.nan
                    # 14:30→引けリターン
                    last30 = prev_day[prev_day['timestamp'].dt.time >= datetime.strptime('14:30','%H:%M').time()]
                    if not last30.empty:
                        o2 = last30.iloc[0]['open']
                        c2 = last30.iloc[-1]['close']
                        rec['prev_day_last30min_return'] = (c2 - o2) / o2 if o2 else np.nan
                    else:
                        rec['prev_day_last30min_return'] = np.nan
                else:
                    rec['prev_day_return'] = np.nan
                    rec['prev_day_range_pct'] = np.nan
                    rec['prev_day_last30min_return'] = np.nan
            else:
                df_today = None
                last_20d_daily = None
                rec['prev_day_volume'] = np.nan
                rec['prev_day_volume_ratio_20d'] = np.nan
                rec['prev_day_return'] = np.nan
                rec['prev_day_range_pct'] = np.nan
                rec['prev_day_last30min_return'] = np.nan
            # --- ギャップ・today初期化 ---
            if df_all is not None and not prev_day.empty and df_today is not None:
                if not df_today.empty:
                    open_today = df_today.iloc[0]['open']
                    close_prev = prev_day.iloc[-1]['close']
                    gap_pct = (open_today - close_prev) / close_prev if close_prev else np.nan
                    rec['gap_pct'] = gap_pct
                    if abs(gap_pct) < 0.003:
                        rec['gap_direction'] = 'none'
                    elif gap_pct > 0:
                        rec['gap_direction'] = 'up'
                    else:
                        rec['gap_direction'] = 'down'
                else:
                    rec['gap_pct'] = np.nan
                    rec['gap_direction'] = 'none'
            else:
                rec['gap_pct'] = np.nan
                rec['gap_direction'] = 'none'
            # --- レベル構造 ---
            lvlist = levels.get(symbol, [])
            # 寄値±0.3%に存在するレベル数・strength合計（lv['level_now']基準）
            if df_all is not None and df_today is not None and not df_today.empty:
                open_today = df_today.iloc[0]['open']
                near_levels = [lv for lv in lvlist if 'level_now' in lv and abs(lv['level_now'] - open_today) / open_today < 0.003]
                rec['num_levels_near_open'] = len(near_levels)
                rec['sum_level_strength_near_open'] = sum(lv.get('strength',0) for lv in near_levels)
                # 日足サポート
                supports = [lv for lv in lvlist if lv.get('kind') in ['pivot_low','consolidation','psychological'] and 'level_now' in lv and lv['level_now'] < open_today]
                if supports:
                    support = max(supports, key=lambda lv: lv['level_now'])
                    # ATR計算（過去20日）
                    if last_20d_daily is not None and len(last_20d_daily) > 0:
                        atr = (last_20d_daily['high'] - last_20d_daily['low']).mean()
                        dist = (open_today - support['level_now']) / atr if atr else np.nan
                        rec['daily_support_dist_atr'] = dist
                        rec['is_daily_support_near'] = (dist is not None) and (dist >= 0) and (dist <= 0.3)
                    else:
                        rec['is_daily_support_near'] = False
                        rec['daily_support_dist_atr'] = np.nan
                else:
                    rec['is_daily_support_near'] = False
                    rec['daily_support_dist_atr'] = np.nan
            else:
                rec['num_levels_near_open'] = np.nan
                rec['sum_level_strength_near_open'] = np.nan
                rec['is_daily_support_near'] = False
                rec['daily_support_dist_atr'] = np.nan
            # --- 当日初動 ---
            if df_all is not None and df_today is not None and not df_today.empty:
                # 5分足データ抽出
                min5 = df_today[df_today['timestamp'].dt.time < (datetime.strptime('09:05','%H:%M').time())]
                if not min5.empty:
                    open_5min_vol = min5['volume'].sum()
                    # 過去5日平均5分出来高
                    past5 = df_all[df_all['timestamp'] < trade_date]
                    past5 = past5[past5['timestamp'].dt.time < (datetime.strptime('09:05','%H:%M').time())]
                    past5 = past5.groupby(past5['timestamp'].dt.date)['volume'].sum().tail(5)
                    mean5 = past5.mean() if not past5.empty else np.nan
                    rec['open_5min_volume_ratio'] = open_5min_vol / mean5 if mean5 else np.nan
                    # 5分値幅
                    o5 = min5.iloc[0]['open']
                    h5 = min5['high'].max()
                    l5 = min5['low'].min()
                    rec['open_5min_range_pct'] = (h5 - l5) / o5 if o5 else np.nan
                    rec['early_volatility_score'] = rec['open_5min_volume_ratio'] * rec['open_5min_range_pct'] if rec['open_5min_volume_ratio'] and rec['open_5min_range_pct'] else np.nan
                else:
                    rec['open_5min_volume_ratio'] = np.nan
                    rec['open_5min_range_pct'] = np.nan
                    rec['early_volatility_score'] = np.nan
            else:
                rec['open_5min_volume_ratio'] = np.nan
                rec['open_5min_range_pct'] = np.nan
                rec['early_volatility_score'] = np.nan
            # --- 板・需給（寄り後複数窓で集約・リークなし設計） ---
            md = market_data_fixed.get(symbol)
            if md is not None and not md.empty:
                md_day = md[md['timestamp'].dt.date == trade_date.date()].sort_values('timestamp')
                # --- デバッグ出力: 1銘柄・1日だけカラム確認 ---
                if symbol == symbols[0]:
                    print("LOB columns sample:", md_day.columns.tolist()[:50])
                    req = [f"bid{i}_price" for i in range(1,6)] + [f"ask{i}_price" for i in range(1,6)]
                    print("Has required price cols:", {c: (c in md_day.columns) for c in req})
                if not md_day.empty:
                    # 生板から特徴量計算
                    md_feat = compute_lob_features_from_raw(md_day, roll_n=20, k_depth=5)
                    # ⚠️ リーク防止: 寄り後X分間のみ集計（実運用で取得可能な窓のみ）
                    # 窓1: 9:00-9:05（5分）→ 9:05以降エントリー想定
                    open_5m = md_feat[(md_feat['timestamp'].dt.time >= datetime.strptime('09:00','%H:%M').time()) & (md_feat['timestamp'].dt.time < datetime.strptime('09:05','%H:%M').time())]
                    rec['ofi_open_5m_mean'] = open_5m['ofi_20'].mean()
                    rec['micro_bias_open_5m_mean'] = open_5m['micro_bias'].mean()
                    rec['depth_imb_open_5m_mean'] = open_5m['depth_imb_5'].mean()
                    
                    # 窓2: 9:00-9:10（10分）→ 9:10以降エントリー想定
                    open_10m = md_feat[(md_feat['timestamp'].dt.time >= datetime.strptime('09:00','%H:%M').time()) & (md_feat['timestamp'].dt.time < datetime.strptime('09:10','%H:%M').time())]
                    rec['ofi_open_10m_mean'] = open_10m['ofi_20'].mean()
                    rec['micro_bias_open_10m_mean'] = open_10m['micro_bias'].mean()
                    rec['depth_imb_open_10m_mean'] = open_10m['depth_imb_5'].mean()
                    
                    # 窓3: 9:00-9:15（15分）→ 9:15以降エントリー想定
                    open_15m = md_feat[(md_feat['timestamp'].dt.time >= datetime.strptime('09:00','%H:%M').time()) & (md_feat['timestamp'].dt.time < datetime.strptime('09:15','%H:%M').time())]
                    rec['ofi_open_15m_mean'] = open_15m['ofi_20'].mean()
                    rec['micro_bias_open_15m_mean'] = open_15m['micro_bias'].mean()
                    rec['depth_imb_open_15m_mean'] = open_15m['depth_imb_5'].mean()
                    
                    # 後方互換性のため旧名も残す（5分窓と同じ）
                    rec['mean_micro_bias_morning'] = rec['micro_bias_open_5m_mean']
                    rec['mean_ofi_morning'] = rec['ofi_open_5m_mean']
                    rec['mean_depth_imb_morning'] = rec['depth_imb_open_5m_mean']
                else:
                    for win in ['5m', '10m', '15m']:
                        rec[f'ofi_open_{win}_mean'] = np.nan
                        rec[f'micro_bias_open_{win}_mean'] = np.nan
                        rec[f'depth_imb_open_{win}_mean'] = np.nan
                    rec['mean_micro_bias_morning'] = np.nan
                    rec['mean_ofi_morning'] = np.nan
                    rec['mean_depth_imb_morning'] = np.nan
            else:
                for win in ['5m', '10m', '15m']:
                    rec[f'ofi_open_{win}_mean'] = np.nan
                    rec[f'micro_bias_open_{win}_mean'] = np.nan
                    rec[f'depth_imb_open_{win}_mean'] = np.nan
                rec['mean_micro_bias_morning'] = np.nan
                rec['mean_ofi_morning'] = np.nan
                rec['mean_depth_imb_morning'] = np.nan
            records.append(rec)
    # DataFrame化
    features_df = pd.DataFrame(records)
    # --- 結果ラベル集計 ---
    if not trades_df.empty:
        trades_df['trade_date'] = pd.to_datetime(trades_df['entry_ts']).dt.strftime('%Y-%m-%d')
        label_df = trades_df.groupby(['symbol','trade_date']).agg(
            num_trades = ('pnl_tick','count'),
            total_pnl = ('pnl_tick','sum'),
            avg_pnl_per_trade = ('pnl_tick','mean')
        ).reset_index()
        # win_rate, has_tradeを後処理で追加
        def calc_win_rate(subdf):
            return (subdf['pnl_tick'] > 0).sum() / len(subdf) if len(subdf) > 0 else 0
        win_rate_df = trades_df.groupby(['symbol','trade_date']).apply(calc_win_rate).reset_index(name='win_rate')
        label_df = label_df.merge(win_rate_df, on=['symbol','trade_date'], how='left')
        label_df['has_trade'] = label_df['num_trades'] > 0
    else:
        label_df = pd.DataFrame(columns=['symbol','trade_date','num_trades','total_pnl','avg_pnl_per_trade','win_rate','has_trade'])
    # LEFT JOIN
    merged = features_df.merge(label_df, on=['symbol','trade_date'], how='left')
    # NaN埋め
    merged['num_trades'] = merged['num_trades'].fillna(0).astype(int)
    merged['total_pnl'] = merged['total_pnl'].fillna(0)
    merged['avg_pnl_per_trade'] = merged['avg_pnl_per_trade'].fillna(0)
    merged['win_rate'] = merged['win_rate'].fillna(0)
    merged['has_trade'] = merged['has_trade'].fillna(False)
    return merged
