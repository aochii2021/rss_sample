from dataclasses import dataclass
from typing import Optional, List


@dataclass
class IntradayConfig:
    resample_minutes: int = 3
    tz: str = "Asia/Tokyo"


@dataclass
class VolumeProfileConfig:
    lookback_days: int = 2  # 前日・前々日
    n_nodes: int = 5        # 主要な価格帯別出来高ノード数
    band_pct: float = 0.002  # サポート帯の幅（0.2%）


@dataclass
class DailySupportConfig:
    swing_lookback: int = 5  # スイング高安検出の窓
    min_slope_abs: float = 0.0  # 斜めトレンドラインの最小傾き（将来拡張）


@dataclass
class StrategyConfig:
    buy_only: bool = True
    risk_rr: float = 1.5           # 利確:損切りの比
    stop_pct: float = 0.005        # 損切り幅（0.5%）
    take_pct: Optional[float] = None  # Noneの場合はRRから決定
    max_trades_per_day: int = 3
    entry_confirm_candles: int = 1  # 反発確認の本数


@dataclass
class BacktestConfig:
    cash: int = 1_000_000
    size: int = 100
    fee_pct: float = 0.0005
    slippage_pct: float = 0.0005


@dataclass
class ProjectConfig:
    tick_csv_path: Optional[str] = None  # 1分〜数分足CSV（JPカラム）
    daily_csv_path: Optional[str] = None  # 日足CSV（JPカラム）
    output_dir: str = "output"
    symbols: Optional[List[str]] = None


@dataclass
class Config:
    intraday: IntradayConfig = IntradayConfig()
    volume_profile: VolumeProfileConfig = VolumeProfileConfig()
    daily_support: DailySupportConfig = DailySupportConfig()
    strategy: StrategyConfig = StrategyConfig()
    backtest: BacktestConfig = BacktestConfig()
    project: ProjectConfig = ProjectConfig()
