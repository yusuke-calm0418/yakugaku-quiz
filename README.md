# yakugaku-quiz

薬剤師国家試験対策向けの Django 製クイズアプリです。  
ユーザー登録・ログイン後に、分野別/苦手問題モードで演習できます。

## 主な機能

- ユーザー登録、ログイン、ログアウト
- 4択クイズ（必須問題: 単一選択 / 一般問題: 複数選択）
- 回答履歴の保存
- 正答率の表示
- 苦手問題モード（同一問題で一定回数以上回答し、正答率が低い問題を抽出）
- 管理画面から問題/回答データを管理

## 技術スタック

- Python 3.12
- Django
- PostgreSQL 15
- Docker / Docker Compose

## ディレクトリ構成（抜粋）

```text
.
├── config/         # Django設定
├── accounts/       # 認証周り + トップ/マイページビュー
├── quiz/           # 問題/回答モデル、クイズロジック
├── templates/      # HTMLテンプレート
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── manage.py
```

## セットアップ（Docker）

1. イメージをビルド

```bash
docker compose build
```

2. コンテナを起動

```bash
docker compose up -d
```

3. マイグレーションを実行

```bash
docker compose exec web python manage.py migrate
```

4. 管理ユーザーを作成（任意）

```bash
docker compose exec web python manage.py createsuperuser
```

5. ブラウザで確認

- アプリ: http://localhost:8000/
- 管理画面: http://localhost:8000/admin/

## 初期データ登録

問題データは管理画面から登録できます。

1. 管理画面にログイン
2. Question で問題文・選択肢・正解・解説・分野・問題種別を入力

### `correct` フィールド入力ルール

- 必須問題（単一選択）: `1` 〜 `4`
- 一般問題（複数選択）: `13` のように正解番号を連結

## 動作確認の流れ

1. 新規登録: `/accounts/signup/`
2. ログイン: `/accounts/login/`
3. クイズ実施: `/quiz/`
4. マイページ確認: `/mypage/`

## テスト

```bash
docker compose exec web python manage.py test
```

## 補足

- 開発用設定のため `DEBUG=True` です。
- メール送信はコンソールバックエンドを使用しているため、パスワードリセットメールはコンテナログに出力されます。
