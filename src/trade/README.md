# 実トレードシステム（algo4_counter_trade）

algo4_counter_tradeの逆張り戦略を実際の市場で実行するためのシステム。

## 概要

- **戦略**: LOB（板情報）ベースの逆張り（ミーンリバージョン）
- **データソース**: MarketSpeed II RSS
- **対象銘柄**: Watchlistに登録された銘柄
- **取引時間**: 前場（9:00-11:30）、後場（12:30-15:15）

## システム構成

### 1. `config.py`
- 取引設定（パラメータ、リスク管理）
- MarketSpeed II RSS接続設定
- ロギング設定

### 2. `live_data_collector.py`
- リアルタイム板情報取得
- LOB特徴量計算
- サポート/レジスタンスレベル更新

### 3. `signal_generator.py`
- エントリー/エグジットシグナル生成
- algo4_counter_tradeのロジックを実装

### 4. `order_executor.py`
- 注文実行（MarketSpeed II経由）
- ポジション管理
- リスク管理

### 5. `main.py`
- メインループ
- システム起動/停止

## 使用方法

```powershell
# 設定ファイル編集
code src/trade/config.py

# 実トレード開始
python src/trade/main.py
```

## 安全機能

- 最大ポジション数制限
- 1日の最大損失制限
- セッション終了時の自動決済
- 緊急停止機能

## ログ

- `logs/trade_YYYYMMDD.log`: トレードログ
- `logs/position_YYYYMMDD.csv`: ポジション履歴
- `logs/order_YYYYMMDD.csv`: 注文履歴
