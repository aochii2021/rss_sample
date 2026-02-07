import pandas as pd
from typing import Dict, Any, Tuple

def load_symbol_day_features(csv_path: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    symbol_day_features.csv を (symbol, trade_date) → dict で返す
    """
    df = pd.read_csv(csv_path, dtype={"symbol": str, "trade_date": str})
    features_dict = {}
    for _, row in df.iterrows():
        features_dict[(row["symbol"], row["trade_date"])] = row.to_dict()
    return features_dict
