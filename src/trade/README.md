# 実トレードシステム（algo4_counter_trade）

algo4_counter_tradeの逆張り戦略を実際の市場で実行するためのシステム。

## 概要

- **戦略**: LOB（板情報）ベースの逆張り（ミーンリバージョン）
- **取引方法**: 信用取引（いちにち信用）
- **データソース**: MarketSpeed II RSS
- **対象銘柄**: Watchlistに登録された銘柄
- **取引時間**: 前場（9:00-11:25）、後場（12:30-15:10）

## 前提条件

### 必須ソフトウェア
1. **楽天証券 MarketSpeed II** がインストール済み
2. **Microsoft Excel** がインストール済み
3. **Python 3.x** + 以下のパッケージ
   - `pywin32` (Excel COM接続用)

### Excel設定
MarketSpeed IIのRSS関数を使用するため、Excelが起動している必要があります：
```powershell
pip install pywin32
```

### 信用取引口座
楽天証券の信用取引口座が開設済みである必要があります。

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
- 信用新規注文実行（RssMarginOpenOrder）
- 信用返済注文実行（RssMarginCloseOrder）
- ポジション管理
- リスク管理（最大ポジション数、損失限度）

### 5. `main.py`
- メインループ
- システム起動/停止

## 使用方法

### 1. DRY_RUNモードでテスト
```powershell
# config.pyでDRY_RUN=Trueを確認（デフォルト）
python src/trade/main.py
```

### 2. 本番モード
```powershell
# config.pyを編集
# DRY_RUN = False に変更
# MARGIN_PARAMS（信用区分、口座区分）を確認

# Excelを起動（MarketSpeed II RSSが使用可能な状態）

# 実トレード開始
python src/trade/main.py
# ⚠️ 本番モード確認メッセージが表示されます
```

## 信用取引設定（config.py）

### 信用区分（margin_type）
- `"1"`: 制度信用（6ヶ月）- 金利安い、貸株料あり
- `"2"`: 一般信用（無制限）- 金利高い
- `"3"`: 一般信用（14日）- 期限付き
- `"4"`: 一般信用（いちにち）⭐デフォルト - 手数料安い、当日返済限定

### 口座区分（account_type）
- `"0"`: 特定口座⭐デフォルト - 確定申告簡単
- `"1"`: 一般口座 - 自分で確定申告

## 注文実行フロー

1. **エントリー**: RssMarginOpenOrder
   - 指値注文（本日中）
   - 買建 or 売建

2. **決済**: RssMarginCloseOrder
   - 指値注文（本日中）
   - 買埋 or 売埋
   - TP（利確）/ SL（損切）/ TO（タイムアウト）

## 安全機能

- **DRY_RUNモード**: 本番前のテスト実行（デフォルト）
- **最大ポジション数制限**: 同時保有最大3銘柄
- **1日の最大損失制限**: 100tick超えで取引停止
- **緊急停止**: 連続5敗 OR 50tick DDで自動停止
- **セッション終了時の自動決済**: 15:10に全ポジション強制決済
- **本番モード確認**: DRY_RUN=False時に起動確認メッセージ

## ログ

- `logs/trade_YYYYMMDD.log`: トレードログ
- `logs/position_YYYYMMDD.csv`: ポジション履歴
- `logs/order_YYYYMMDD.csv`: 注文履歴
