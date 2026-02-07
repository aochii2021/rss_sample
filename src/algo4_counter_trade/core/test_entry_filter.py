from entry_filter import EnvironmentFilter, EnvFilterThresholds

# テスト用サンプル
features_ok = {
    "prev_day_volume_ratio_20d": 1.2,
    "prev_day_last30min_return": 0.01,
    "daily_support_dist_atr": 0.02
}
features_ng1 = {
    "prev_day_volume_ratio_20d": 1.0,
    "prev_day_last30min_return": 0.01,
    "daily_support_dist_atr": 0.02
}
features_ng2 = {
    "prev_day_volume_ratio_20d": 1.2,
    "prev_day_last30min_return": -0.02,
    "daily_support_dist_atr": 0.02
}
features_ng3 = {
    "prev_day_volume_ratio_20d": 1.2,
    "prev_day_last30min_return": 0.01,
    "daily_support_dist_atr": 0.03
}
features_nan = {
    "prev_day_volume_ratio_20d": float('nan'),
    "prev_day_last30min_return": 0.01,
    "daily_support_dist_atr": 0.02
}
features_none = {
    "prev_day_volume_ratio_20d": None,
    "prev_day_last30min_return": 0.01,
    "daily_support_dist_atr": 0.02
}

filt = EnvironmentFilter()
print("OK:", filt.allow(features_ok))
print("NG1:", filt.allow(features_ng1))
print("NG2:", filt.allow(features_ng2))
print("NG3:", filt.allow(features_ng3))
print("NaN:", filt.allow(features_nan))
print("None:", filt.allow(features_none))
