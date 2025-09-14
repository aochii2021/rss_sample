# Contributing to Stock Analysis Project

## はじめに
このプロジェクトへの貢献をお考えいただき、ありがとうございます。以下のガイドラインに従って、効果的にプロジェクトに参加してください。

## コントリビューション方法

### 1. Issue の作成
- バグ報告やフィーチャーリクエストは Issue で作成してください
- 明確で具体的な内容を記載してください
- 適切なラベルを付けてください

### 2. Pull Request の手順
1. このリポジトリをフォークする
2. フィーチャーブランチを作成する (`git checkout -b feature/new-algorithm`)
3. 変更をコミットする (`git commit -am 'Add new trading algorithm'`)
4. ブランチをプッシュする (`git push origin feature/new-algorithm`)
5. Pull Request を作成する

### 3. コーディング規則
- [DEVELOPMENT_POLICY.md](../DEVELOPMENT_POLICY.md) に記載された開発方針に従ってください
- GitHub Copilot を使用する際は、生成されたコードを必ず検証してください
- 金融データを扱う際は特に慎重にテストを行ってください

### 4. テスト
- 新機能には適切なテストを追加してください
- 既存のテストが通ることを確認してください
- 金融計算の精度について特に注意してください

### 5. ドキュメント
- 新しいアルゴリズムには README.md を追加してください
- API の変更があれば適切に文書化してください

## セットアップ

```bash
# 依存関係のインストール
pip install -r requirements.txt

# テストの実行
python -m pytest

# コードフォーマット
black src/
```

## 質問・サポート
ご質問がある場合は、Issue を作成するか、Discussion をご利用ください。
