# src/trade/lob_features.py
# algo4 legacy lob_features.py のラッパー
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../algo4_counter_trade/legacy')))
from lob_features import compute_features_ms2
