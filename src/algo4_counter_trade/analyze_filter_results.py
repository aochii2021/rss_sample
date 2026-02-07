"""
フィルタ効果の詳細分析
罠①：銘柄偏り、罠②：データリーク の検証
"""
import pandas as pd
import sys
from pathlib import Path

def analyze_filter_results(run_dir):
    """フィルタ適用結果を分析"""
    trades_path = Path(run_dir) / 'output' / 'trades.csv'
    perf_path = Path(run_dir) / 'output' / 'performance_by_symbol_date.csv'
    
    if not trades_path.exists():
        print(f"❌ {trades_path} が見つかりません")
        return
    
    df_trades = pd.read_csv(trades_path)
    df_perf = pd.read_csv(perf_path)
    
    print("=" * 70)
    print("📊 フィルタ効果分析レポート")
    print("=" * 70)
    
    # ========================================
    # 罠① 銘柄偏りチェック
    # ========================================
    print("\n【罠①】銘柄偏りチェック")
    print("-" * 70)
    
    # 銘柄別集計
    symbol_stats = df_trades.groupby('symbol').agg({
        'pnl_tick': ['sum', 'count', 'mean']
    })
    symbol_stats.columns = ['total_pnl', 'trade_count', 'avg_pnl']
    symbol_stats = symbol_stats.sort_values('total_pnl', ascending=False)
    symbol_stats['trade_pct'] = symbol_stats['trade_count'] / len(df_trades) * 100
    
    print("\n✅ 銘柄別PnL上位15件:")
    print(symbol_stats[['trade_count', 'trade_pct', 'total_pnl', 'avg_pnl']].head(15).to_string())
    
    print("\n✅ トレード数上位15銘柄:")
    top_by_count = symbol_stats.sort_values('trade_count', ascending=False).head(15)
    print(top_by_count[['trade_count', 'trade_pct', 'total_pnl', 'avg_pnl']].to_string())
    
    # 集中度指標
    top1_pct = symbol_stats.iloc[0]['trade_pct']
    top5_pct = symbol_stats.head(5)['trade_pct'].sum()
    top10_pct = symbol_stats.head(10)['trade_pct'].sum()
    
    print(f"\n📈 集中度指標:")
    print(f"  Top1銘柄: {top1_pct:.1f}% (⚠️30%超で偏り強)")
    print(f"  Top5合計: {top5_pct:.1f}%")
    print(f"  Top10合計: {top10_pct:.1f}%")
    
    if top1_pct > 30:
        print(f"  ⚠️ 警告: Top1が{top1_pct:.1f}%で偏りが強い")
    elif top1_pct > 20:
        print(f"  ⚡ 注意: Top1が{top1_pct:.1f}%でやや偏りあり")
    else:
        print(f"  ✅ OK: 分散されている")
    
    # ========================================
    # 日別PnL推移（安定性チェック）
    # ========================================
    print("\n" + "=" * 70)
    print("【安定性】日別PnL推移")
    print("-" * 70)
    
    # CSVのカラム名を確認
    print(f"\ntrades.csv カラム: {df_trades.columns.tolist()}")
    
    # entry_tsから日付を抽出
    df_trades['entry_date'] = pd.to_datetime(df_trades['entry_ts']).dt.date
    
    daily_pnl = df_trades.groupby('entry_date').agg({
        'pnl_tick': 'sum',
        'symbol': 'count'
    }).rename(columns={'symbol': 'trades'})
    daily_pnl['cumsum'] = daily_pnl['pnl_tick'].cumsum()
    daily_pnl['avg_per_trade'] = daily_pnl['pnl_tick'] / daily_pnl['trades']
    
    print(f"\n✅ 日別PnL推移:")
    print(daily_pnl.to_string())
    
    # 統計
    profitable_days = (daily_pnl['pnl_tick'] > 0).sum()
    total_days = len(daily_pnl)
    
    print(f"\n📊 日別統計:")
    print(f"  プラス日数: {profitable_days}/{total_days} ({profitable_days/total_days*100:.1f}%)")
    print(f"  最良日: {daily_pnl['pnl_tick'].max():.1f} tick ({daily_pnl['pnl_tick'].idxmax()})")
    print(f"  最悪日: {daily_pnl['pnl_tick'].min():.1f} tick ({daily_pnl['pnl_tick'].idxmin()})")
    print(f"  日別PnL標準偏差: {daily_pnl['pnl_tick'].std():.1f} tick")
    
    # ========================================
    # 罠② データリーク可能性チェック
    # ========================================
    print("\n" + "=" * 70)
    print("【罠②】データリーク可能性チェック")
    print("-" * 70)
    
    print("\n✅ 確認すべき設計ポイント:")
    print("  1. symbol_day_features.csv の特徴量計算タイミング")
    print("     → daily_support_dist_atr は「前日終値時点」で計算済みか？")
    print("     → prev_day_* は文字通り「前営業日」のデータか？")
    print("  2. trade_date列の付与タイミング")
    print("     → load_market_data_for_date() で「当日日付」として正しく設定されているか")
    print("  3. フィルタ適用タイミング")
    print("     → backtest_engine.py でエントリー判定「前」にフィルタされているか")
    
    # 特徴量ファイルの時系列チェック
    feature_path = Path(__file__).parent.parent / 'analysis' / 'symbol_day_features.csv'
    if feature_path.exists():
        df_feat = pd.read_csv(feature_path)
        print(f"\n✅ symbol_day_features.csv 読み込み成功")
        print(f"  総レコード数: {len(df_feat)}")
        
        # カラム名を確認
        if 'trade_date' in df_feat.columns:
            date_col = 'trade_date'
        elif 'business_day' in df_feat.columns:
            date_col = 'business_day'
        else:
            date_col = df_feat.columns[1]  # 2列目を日付とみなす
        
        print(f"  日付範囲: {df_feat[date_col].min()} ~ {df_feat[date_col].max()}")
        
        # has_trade=Trueの最終日を確認
        if 'has_trade' in df_feat.columns:
            train_last = df_feat[df_feat['has_trade'] == True][date_col].max()
            all_last = df_feat[date_col].max()
            print(f"\n  📅 学習データ最終日: {train_last}")
            print(f"  📅 全データ最終日: {all_last}")
            
            if train_last < all_last:
                print(f"  ✅ OK: 学習期間({train_last})より後のデータ({all_last})でテスト")
            else:
                print(f"  ⚠️ 警告: 学習期間とテスト期間が重複している可能性")
        
        # 特徴量カラムの確認
        feature_cols = [col for col in df_feat.columns if col not in ['symbol', date_col, 'num_trades', 'total_pnl', 'avg_pnl_per_trade', 'win_rate', 'has_trade']]
        print(f"\n  📊 特徴量カラム数: {len(feature_cols)}")
        print(f"  主要特徴量: {feature_cols[:10]}")
        
        # データリーク疑いのあるカラムをチェック
        suspect_cols = [col for col in df_feat.columns if any(x in col.lower() for x in ['pnl', 'win', 'trade', 'return']) and col not in ['prev_day_return', 'prev_day_last30min_return']]
        if suspect_cols:
            print(f"\n  ⚠️ リーク疑いのあるカラム: {suspect_cols}")
            print(f"     → これらが特徴量に含まれていないことを確認してください")
    else:
        print(f"\n⚠️ {feature_path} が見つかりません")
    
    # ========================================
    # 取引コスト耐性チェック
    # ========================================
    print("\n" + "=" * 70)
    print("【取引コスト】耐性チェック")
    print("-" * 70)
    
    avg_pnl = df_trades['pnl_tick'].mean()
    median_pnl = df_trades['pnl_tick'].median()
    
    print(f"\n現在の平均PnL: {avg_pnl:.2f} tick/trade")
    print(f"中央値PnL: {median_pnl:.2f} tick/trade")
    
    # コスト想定
    costs = {
        '手数料のみ': 0.5,
        '手数料+スリッページ': 1.0,
        '手数料+スリッページ+呼値不利': 1.5,
        '実運用想定（厳しめ）': 2.0
    }
    
    print(f"\n✅ コスト控除後の期待値（片道）:")
    for name, cost in costs.items():
        net_pnl = avg_pnl - cost
        print(f"  {name:25s}: {net_pnl:+.2f} tick/trade", end="")
        if net_pnl > 0:
            print(" ✅")
        elif net_pnl > -0.5:
            print(" ⚡（ギリギリ）")
        else:
            print(" ❌")
    
    print("\n📝 推奨:")
    if avg_pnl < 1.5:
        print("  ⚠️ 平均PnLが低い → フィルタを強化してトレード数を更に削減すべき")
    elif avg_pnl < 2.5:
        print("  ⚡ 平均PnLは実用ギリギリ → 実運用前にスリッページ計測推奨")
    else:
        print("  ✅ 平均PnLは十分 → 実運用可能性あり")
    
    # ========================================
    # 総合評価
    # ========================================
    print("\n" + "=" * 70)
    print("【総合評価】")
    print("-" * 70)
    
    issues = []
    if top1_pct > 30:
        issues.append(f"⚠️ Top1銘柄が{top1_pct:.1f}%と偏りが強い → 銘柄フィルタを追加検討")
    elif top1_pct > 20:
        issues.append(f"⚡ Top1銘柄が{top1_pct:.1f}%とやや偏り → 監視が必要")
    
    if avg_pnl < 1.5:
        issues.append(f"⚠️ 平均PnL {avg_pnl:.2f} tick は実運用では厳しい → フィルタ強化を")
    
    if len(daily_pnl) > 0 and profitable_days / total_days < 0.4:
        issues.append(f"⚠️ プラス日が{profitable_days/total_days*100:.1f}%と少ない → 不安定")
    
    if len(issues) == 0:
        print("\n✅ クリーンな結果です。フィルタは正しく機能しています。")
        print("   次のステップ:")
        print("   1. より長期のOOSデータで検証")
        print("   2. フィルタ閾値のパラメータチューニング")
        print("   3. 他のleaf_idルールとの組み合わせ検証")
    else:
        print("\n⚡ 以下の点に注意が必要:")
        for issue in issues:
            print(f"   {issue}")
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_dir = sys.argv[1]
    else:
        run_dir = 'runs/20260206_001034'
    
    analyze_filter_results(run_dir)
