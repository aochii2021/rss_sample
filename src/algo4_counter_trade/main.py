from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from .config import Config
from .data_loader import load_intraday_csv, resample_to_minutes, load_daily_csv
from .support import volume_profile_support, recent_horizontal_support
from .strategy import generate_signals
from .backtest import evaluate_trades, plot_trades


def run(args: argparse.Namespace):
    cfg = Config()
    if args.stop_pct is not None:
        cfg.strategy.stop_pct = args.stop_pct
    if args.risk_rr is not None:
        cfg.strategy.risk_rr = args.risk_rr
    if args.take_pct is not None:
        cfg.strategy.take_pct = args.take_pct

    intraday = load_intraday_csv(args.intraday)
    df3 = resample_to_minutes(intraday, minutes=cfg.intraday.resample_minutes)
    daily = load_daily_csv(args.daily) if args.daily else None

    zones = volume_profile_support(df3, n_nodes=cfg.volume_profile.n_nodes,
                                   lookback_days=cfg.volume_profile.lookback_days,
                                   band_pct=cfg.volume_profile.band_pct)
    if daily is not None:
        _ = recent_horizontal_support(daily, lookback=cfg.daily_support.swing_lookback)

    trades = generate_signals(df3, zones, cfg.strategy)
    trades_df = evaluate_trades(df3, trades, size=cfg.backtest.size,
                                fee_pct=cfg.backtest.fee_pct, slippage_pct=cfg.backtest.slippage_pct)

    out_dir = Path(args.output or "output")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "trades.csv"
    trades_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Saved trades -> {out_csv}")

    if args.plot:
        plot_trades(df3, trades_df)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="algo4 counter trade backtest")
    p.add_argument("--intraday", required=True, help="intraday CSV path (JP columns)")
    p.add_argument("--daily", required=False, help="daily CSV path (JP columns)")
    p.add_argument("--output", required=False, help="output directory")
    p.add_argument("--stop_pct", type=float, required=False)
    p.add_argument("--risk_rr", type=float, required=False)
    p.add_argument("--take_pct", type=float, required=False)
    p.add_argument("--plot", action="store_true")
    return p


if __name__ == "__main__":
    parser = build_parser()
    run(parser.parse_args())
