# 貢献ガイド

PyPSGEmuプロジェクトへの貢献を歓迎します！このドキュメントでは、プロジェクトへの貢献方法について説明します。

## 貢献の種類

以下のような貢献を歓迎します：

- 🐛 バグレポート
- 💡 機能提案
- 📝 ドキュメントの改善
- 🧪 テストの追加・改善
- 🔧 コードの改善・最適化
- 🌍 国際化・翻訳

## 開発環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/siska-tech/pypsgemu.git
cd pypsgemu
```

### 2. 開発環境のインストール

```bash
# 仮想環境の作成（推奨）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows

# 開発依存関係のインストール
pip install -e ".[dev]"
```

### 3. 事前コミットフックの設定（オプション）

```bash
pre-commit install
```

## 開発フロー

### 1. ブランチの作成

```bash
git checkout -b feature/your-feature-name
# または
git checkout -b bugfix/your-bugfix-name
```

### 2. 変更の実装

- コードを書く
- テストを書く
- ドキュメントを更新する

### 3. テストの実行

```bash
# 全テストを実行
python -m pytest

# 特定のテストを実行
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/performance/

# カバレッジレポートの生成
python -m pytest --cov=pypsgemu --cov-report=html
```

### 4. コードフォーマット

```bash
# Black でフォーマット
black pypsgemu/ tests/

# isort でインポートを整理
isort pypsgemu/ tests/

# flake8 でリント
flake8 pypsgemu/ tests/
```

### 5. コミット

```bash
git add .
git commit -m "feat: add new feature description"
```

コミットメッセージは [Conventional Commits](https://www.conventionalcommits.org/) の形式に従ってください：

- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメントの変更
- `style:` フォーマット、セミコロン追加など
- `refactor:` リファクタリング
- `test:` テストの追加・修正
- `chore:` ビルドプロセスやツールの変更

### 6. プッシュとプルリクエスト

```bash
git push origin feature/your-feature-name
```

その後、GitHubでプルリクエストを作成してください。

## コーディング規約

### Python

- [PEP 8](https://pep8.org/) に従う
- 型ヒントを使用する
- ドキュメント文字列を書く
- 適切な例外処理を行う

### テスト

- 全ての新機能にテストを書く
- バグ修正には回帰テストを含める
- テストカバレッジを維持する

### ドキュメント

- README.mdを更新する
- APIドキュメントを更新する
- 必要に応じてユーザーガイドを更新する

## バグレポート

バグを発見した場合は、以下の情報を含めてIssueを作成してください：

1. **問題の概要**
2. **再現手順**
3. **期待される動作**
4. **実際の動作**
5. **環境情報**
   - OS
   - Python バージョン
   - PyPSGEmu バージョン
6. **エラーメッセージやログ**（あれば）

## 機能提案

新機能を提案する場合は、以下の情報を含めてIssueを作成してください：

1. **機能の概要**
2. **使用例**
3. **実装のアイデア**
4. **代替案**（あれば）

## プルリクエストのレビュー

プルリクエストは以下の基準でレビューされます：

- コードの品質
- テストの完全性
- ドキュメントの適切性
- パフォーマンスへの影響
- 後方互換性

## ライセンス

このプロジェクトに貢献することで、あなたの貢献はMITライセンスの下で公開されることに同意したものとみなされます。

## 質問・サポート

質問がある場合は、以下の方法でお気軽にお問い合わせください：

- [GitHub Discussions](https://github.com/siska-tech/pypsgemu/discussions)
- [GitHub Issues](https://github.com/siska-tech/pypsgemu/issues)

---

貢献していただき、ありがとうございます！🎵
