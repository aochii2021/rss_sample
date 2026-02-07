from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class EnvFilterThresholds:
    min_prev_day_volume_ratio_20d: float = 1.07
    min_prev_day_last30min_return: float = -0.0135
    max_daily_support_dist_atr: float = 0.02  # 強化: 0.025 → 0.02（サポート反発の精度向上）
    
    # 板条件（リークなし複数窓対応）
    # 使用する窓に応じてゲート開始時刻を整合させる必要あり
    board_indicator: str = 'micro_bias'  # 'ofi', 'micro_bias', 'depth_imb' のいずれか
    board_window: str = '10m'  # '5m', '10m', '15m' のいずれか
    min_board_threshold: float = 0.0  # 板指標閾値（> この値）
    entry_start_time: str = '09:10:00'  # エントリー開始時刻（窓と整合させる: 5m→09:05, 10m→09:10, 15m→09:15）
    
    # 後方互換性のため残す（非推奨）
    ofi_window: str = '10m'
    min_ofi_threshold: float = 0.0
    min_mean_ofi_morning: float = 0.0

class EnvironmentFilter:
    """
    環境フィルタ（当日稼働するか）
    leaf_id=7 の条件を固定ルールとして実装
    """
    def __init__(self, thresholds: EnvFilterThresholds | None = None):
        self.th = thresholds or EnvFilterThresholds()

    def allow(self, features: Dict[str, Any]) -> bool:
        """
        features: symbol_day_features の 1行分相当（当日判定に必要な列が入る）
        """
        vratio = features.get("prev_day_volume_ratio_20d")
        last30 = features.get("prev_day_last30min_return")
        sdist  = features.get("daily_support_dist_atr")
        
        # 板指標タイプと窓に応じた特徴量を取得
        board_col = f"{self.th.board_indicator}_open_{self.th.board_window}_mean"
        board_value = features.get(board_col)
        
        # 欠損は安全側で拒否（データ不備で取引しない）
        if vratio is None or last30 is None or sdist is None or board_value is None:
            return False
        if any(map(lambda x: x != x, [vratio, last30, sdist, board_value])):  # NaN check
            return False

        return (
            vratio > self.th.min_prev_day_volume_ratio_20d
            and last30 > self.th.min_prev_day_last30min_return
            and sdist <= self.th.max_daily_support_dist_atr
            and board_value > self.th.min_board_threshold
        )
