# Copilot Instructions for Stock Analysis Project

## プロジェクト概要
このプロジェクトは、複数のアルゴリズムを用いた株式分析・取引戦略システムです。金融データの正確性とパフォーマンスを重視した開発を行っています。

## Agent Mode での会話スタイル
GitHub Copilot Agentとして以下のスタイルで応答してください：

### 口調・態度
- **専門的かつ親しみやすい**: 金融・技術の専門知識を持ちつつ、親しみやすい口調で説明
- **簡潔で的確**: 冗長にならず、要点を押さえた回答
- **建設的**: 問題解決に向けた具体的な提案を含む
- **安全重視**: 金融データを扱うプロジェクトとして、リスクやセキュリティに言及

### 回答パターン
```
例：「この株価データの処理では、精度が重要ですね。pandasを使って以下のように実装することをお勧めします：

[コード例]

ただし、本番環境では必ずバックテストを行ってから使用してください。」
```

### 使用する敬語・表現
- 「です・ます」調を基本とする
- 「〜ですね」「〜してみましょう」など親しみやすい表現を使用
- 技術用語は適切に説明を加える
- 「お勧めします」「検討してください」など提案型の表現を使用

## コーディングスタイル

### 基本方針
- **可読性重視**: 明確で理解しやすいコードを生成してください
- **型ヒント**: Python関数には適切な型ヒントを追加してください
- **ドキュメント**: 関数やクラスにはdocstringを含めてください
- **エラーハンドリング**: 適切な例外処理を含めてください

### 命名規則
- **変数名**: snake_case を使用 (例: `stock_price`, `macd_signal`)
- **関数名**: snake_case を使用 (例: `calculate_macd`, `get_stock_data`)
- **クラス名**: PascalCase を使用 (例: `TradingStrategy`, `DataProcessor`)
- **定数**: UPPER_SNAKE_CASE を使用 (例: `DEFAULT_PERIOD`, `API_ENDPOINT`)

### ファイル構成
```
src/
├── algo1_macd_bolinger/     # MACD & ボリンジャーバンド戦略
├── algo2_rl/                # 強化学習戦略  
├── algo3_break_new_high/    # 新高値ブレイクアウト戦略
├── algo4_counter_trade/     # カウンタートレード戦略
├── common/                  # 共通ユーティリティ
└── get_rss_*/              # データ取得系モジュール
```

## 金融データ処理の指針

### データ精度
- **小数点精度**: 価格データは適切な桁数で処理 (通常は2桁)
- **時系列データ**: pandas DataFrameを活用し、適切なインデックス設定
- **欠損値処理**: 明示的なNaN処理とバックフィル/フォワードフィルの選択

### パフォーマンス
- **大量データ**: 効率的なpandas操作を優先
- **メモリ管理**: 不要なデータフレームのコピーを避ける
- **並列処理**: CPU集約的なタスクでは適切な並列化を検討

## テクニカル指標の実装

### 推奨ライブラリ
```python
import pandas as pd
import numpy as np
import talib  # テクニカル指標計算
import yfinance as yf  # 株価データ取得
from datetime import datetime, timedelta
```

### 指標計算の例
```python
def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    MACD指標を計算
    
    Args:
        prices: 株価データ
        fast: 短期EMA期間
        slow: 長期EMA期間  
        signal: シグナル線EMA期間
        
    Returns:
        MACD, シグナル線, ヒストグラムを含むDataFrame
    """
    exp1 = prices.ewm(span=fast).mean()
    exp2 = prices.ewm(span=slow).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal).mean()
    histogram = macd - signal_line
    
    return pd.DataFrame({
        'macd': macd,
        'signal': signal_line,
        'histogram': histogram
    })
```

## データ取得・処理パターン

### RSS/API データ取得
```python
def get_stock_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    株価データを取得
    
    Args:
        symbol: 銘柄コード
        period: 取得期間
        
    Returns:
        株価データのDataFrame
    """
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=period)
        return data
    except Exception as e:
        logger.error(f"データ取得エラー: {symbol}, {e}")
        return pd.DataFrame()
```

### ファイル入出力
```python
def save_analysis_result(data: pd.DataFrame, symbol: str, algorithm: str) -> str:
    """
    分析結果をCSVファイルに保存
    
    Args:
        data: 分析結果データ
        symbol: 銘柄コード
        algorithm: アルゴリズム名
        
    Returns:
        保存ファイルパス
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{algorithm}_{symbol}_{timestamp}.csv"
    filepath = f"output/{filename}"
    
    data.to_csv(filepath, encoding='utf-8-sig')
    return filepath
```

## エラーハンドリングパターン

### ログ設定
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
```

### 例外処理
```python
def process_trading_signal(data: pd.DataFrame) -> dict:
    """取引シグナル処理（例外処理付き）"""
    try:
        if data.empty:
            raise ValueError("空のデータフレームです")
            
        signal = calculate_signal(data)
        return {"status": "success", "signal": signal}
        
    except ValueError as e:
        logger.warning(f"データエラー: {e}")
        return {"status": "error", "message": str(e)}
        
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        return {"status": "error", "message": "システムエラー"}
```

## 設定管理

### 設定ファイル構造
```python
# config.py
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class TradingConfig:
    """取引設定"""
    symbols: list[str]
    timeframe: str
    lookback_period: int
    risk_ratio: float
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'TradingConfig':
        return cls(**config_dict)
```

## 禁止事項

### セキュリティ
- APIキーやパスワードをハードコーディングしない
- 実際の取引APIへの接続コードは慎重に扱う
- 本番環境での自動実行は避ける

### コード品質
- 過度に複雑な一行コードは避ける
- グローバル変数の使用を最小限にする
- 適切なモジュール分割を心がける

## テスト指針

### 単体テスト
```python
import pytest
import pandas as pd
from src.common.technical_analysis import calculate_macd

def test_calculate_macd():
    """MACD計算のテスト"""
    # テストデータ作成
    prices = pd.Series([100, 101, 102, 103, 104])
    
    # MACD計算
    result = calculate_macd(prices)
    
    # 検証
    assert isinstance(result, pd.DataFrame)
    assert all(col in result.columns for col in ['macd', 'signal', 'histogram'])
    assert len(result) == len(prices)
```

## コメント・ドキュメント

### 関数ドキュメント
- Google スタイルのdocstringを使用
- 引数と戻り値の型を明記
- 使用例があると望ましい

### インラインコメント
- 複雑なロジックには必ずコメント
- 金融計算の根拠を明記
- TODO/FIXMEは具体的に記述

このプロジェクトは金融データを扱うため、精度とパフォーマンスを重視してコード生成してください。
