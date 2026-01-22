"""
1/22時点のデータでバックテストを実行するスクリプト
"""
from pathlib import Path
import pandas as pd
import sys
import os

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from algo4_counter_trade.config import Config
from algo4_counter_trade.data_loader import load_intraday_csv, resample_to_minutes, load_daily_csv
from algo4_counter_trade.support import volume_profile_support
from algo4_counter_trade.strategy import generate_signals
from algo4_counter_trade.backtest import evaluate_trades


def run_backtest_for_symbol(symbol: str, base_dir: Path, output_dir: Path):
    """指定された銘柄のバックテストを実行"""
    print(f"\n{'='*60}")
    print(f"バックテスト実行: {symbol}")
    print(f"{'='*60}")
    
    # データファイルパス
    intraday_file = base_dir / "3M_3000_20260122" / f"stock_chart_3M_{symbol}_20251211_20260122.csv"
    daily_file = base_dir / "D_3000_20260122" / f"stock_chart_D_{symbol}_20131010_20260122.csv"
    
    # ファイル存在確認
    if not intraday_file.exists():
        print(f"⚠ 3分足データが見つかりません: {intraday_file}")
        return None
    if not daily_file.exists():
        print(f"⚠ 日足データが見つかりません: {daily_file}")
        daily_file = None
    
    # 設定
    cfg = Config()
    cfg.strategy.stop_pct = 0.005  # 損切り 0.5%
    cfg.strategy.risk_rr = 1.5      # リスクリワード比
    cfg.backtest.size = 100         # 100株
    cfg.backtest.fee_pct = 0.0005   # 手数料 0.05%
    
    try:
        # データ読み込み
        intraday = load_intraday_csv(str(intraday_file))
        df3 = resample_to_minutes(intraday, minutes=cfg.intraday.resample_minutes)
        print(f"3分足データ: {len(df3)}本 ({df3.index[0]} ~ {df3.index[-1]})")
        
        daily = load_daily_csv(str(daily_file)) if daily_file else None
        if daily is not None:
            print(f"日足データ: {len(daily)}本 ({daily.index[0]} ~ {daily.index[-1]})")
        
        # サポートゾーン検出
        zones = volume_profile_support(
            df3, 
            n_nodes=cfg.volume_profile.n_nodes,
            lookback_days=cfg.volume_profile.lookback_days,
            band_pct=cfg.volume_profile.band_pct
        )
        print(f"サポートゾーン: {len(zones)}個検出")
        
        # シグナル生成
        trades = generate_signals(df3, zones, cfg.strategy)
        print(f"トレードシグナル: {len(trades)}個生成")
        
        if len(trades) == 0:
            print("⚠ トレードシグナルが生成されませんでした")
            return None
        
        # バックテスト評価
        trades_df = evaluate_trades(
            df3, trades, 
            size=cfg.backtest.size,
            fee_pct=cfg.backtest.fee_pct, 
            slippage_pct=cfg.backtest.slippage_pct
        )
        
        # 結果保存
        symbol_output_dir = output_dir / symbol
        symbol_output_dir.mkdir(parents=True, exist_ok=True)
        
        trades_csv = symbol_output_dir / "trades.csv"
        trades_df.to_csv(trades_csv, index=False, encoding="utf-8-sig")
        print(f"✓ トレード結果保存: {trades_csv}")
        
        # 統計情報
        stats = {
            "symbol": symbol,
            "total_trades": len(trades_df),
            "winning_trades": len(trades_df[trades_df["pnl"] > 0]),
            "losing_trades": len(trades_df[trades_df["pnl"] < 0]),
            "total_pnl": trades_df["pnl"].sum(),
            "avg_pnl": trades_df["pnl"].mean(),
            "max_profit": trades_df["pnl"].max(),
            "max_loss": trades_df["pnl"].min(),
            "win_rate": len(trades_df[trades_df["pnl"] > 0]) / len(trades_df) * 100 if len(trades_df) > 0 else 0
        }
        
        print(f"\n【統計情報】")
        print(f"総トレード数: {stats['total_trades']}")
        print(f"勝ちトレード: {stats['winning_trades']} ({stats['win_rate']:.1f}%)")
        print(f"負けトレード: {stats['losing_trades']}")
        print(f"総損益: ¥{stats['total_pnl']:,.0f}")
        print(f"平均損益: ¥{stats['avg_pnl']:,.0f}")
        print(f"最大利益: ¥{stats['max_profit']:,.0f}")
        print(f"最大損失: ¥{stats['max_loss']:,.0f}")
        
        return stats
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """メイン処理"""
    # ディレクトリ設定
    project_root = Path(__file__).parent
    data_dir = project_root / "src" / "get_rss_chart_data" / "output"
    output_dir = project_root / "backtest_results_20260122"
    
    # テスト対象銘柄（代表的な銘柄を選定）
    test_symbols = [
        "7203",  # トヨタ自動車
        "6758",  # ソニーグループ
        "9984",  # ソフトバンクグループ
        "8306",  # 三菱UFJフィナンシャル・グループ
        "6501",  # 日立製作所
        "9983",  # ファーストリテイリング
        "4063",  # 信越化学工業
        "6954",  # ファナック
        "7974",  # 任天堂
        "8411",  # みずほフィナンシャルグループ
    ]
    
    print("="*60)
    print("1/22時点データでのバックテスト実行")
    print(f"対象銘柄数: {len(test_symbols)}")
    print(f"データディレクトリ: {data_dir}")
    print(f"出力ディレクトリ: {output_dir}")
    print("="*60)
    
    # 各銘柄でバックテスト実行
    all_stats = []
    for symbol in test_symbols:
        stats = run_backtest_for_symbol(symbol, data_dir, output_dir)
        if stats:
            all_stats.append(stats)
    
    # 全体サマリー
    if all_stats:
        print("\n" + "="*60)
        print("全体サマリー")
        print("="*60)
        
        summary_df = pd.DataFrame(all_stats)
        summary_csv = output_dir / "summary.csv"
        summary_df.to_csv(summary_csv, index=False, encoding="utf-8-sig")
        print(f"✓ サマリー保存: {summary_csv}")
        
        print("\n【銘柄別結果】")
        print(summary_df.to_string(index=False))
        
        print(f"\n【集計】")
        print(f"成功銘柄数: {len(all_stats)} / {len(test_symbols)}")
        print(f"総トレード数: {summary_df['total_trades'].sum()}")
        print(f"平均勝率: {summary_df['win_rate'].mean():.1f}%")
        print(f"総損益合計: ¥{summary_df['total_pnl'].sum():,.0f}")
    else:
        print("\n⚠ 有効な結果が得られませんでした")


if __name__ == "__main__":
    main()
