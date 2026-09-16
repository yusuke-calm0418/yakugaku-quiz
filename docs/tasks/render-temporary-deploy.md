# Render 一時公開対応

## 目的
現在の `yakugaku-quiz` を、本番AWS環境を構築する前の一時公開環境として Render にデプロイできるようにしてください。
今回は **Render の無料枠のみ**を使用する想定です。
最終的な本番環境はAWSを予定しているため、Render向けに既存構成を大きく変更しないでください。
---

## 事前確認
実装前に必ず以下を確認してください。
* `AGENTS.md`
* `docs/project-spec.md`
* `docs/agent/development.md`
* 必要に応じて `docs/agent/design.md`
また、現在の以下の構成を確認してください。

* Django設定
* PostgreSQL設定
* `requirements.txt`
* `Dockerfile`
* `docker-compose.yml`
* static / media の管理方法
* `.env` / 環境変数の利用状況
* Gunicornの導入状況

既存実装を確認したうえで、必要最小限の変更をしてください。

---

# 基本方針

Renderは本番AWS環境ではなく、一時公開用の環境として使用します。
そのため、
* 既存のDocker構成を削除しない
* Docker Composeを削除しない
* Nginx設定を削除しない
* AWS向けの設定を壊さない
* ローカル開発環境を壊さない
ことを必須とします。

Render専用設定を追加する形で対応してください。

---

# Render構成

以下の構成を想定してください。

```text
Render
├── Web Service
│   └── Django
│       ├── Gunicorn
│       └── WhiteNoise
│
└── PostgreSQL
```

Render上ではNginxを使用せず、GunicornでDjangoを起動してください。
staticファイルについてはWhiteNoiseを使用してください。

---

# Render無料枠
以下を使用してください。

## Web Service

```text
plan: free
```

## PostgreSQL
```text
plan: free
```

有料サービスや有料オプションは使用しないでください。
---

# 対応内容
## 1. requirements.txt

現在の依存関係を確認してください。
Renderでの動作に必要で、まだ存在しない場合のみ以下を追加してください。

```text
gunicorn
whitenoise
dj-database-url
psycopg2-binary
```

すでに同等のライブラリが存在する場合は重複追加しないでください。
既存パッケージを不用意にアップグレードしないでください。

---

## 2. Django settings

現在の設定を確認し、ローカル環境とRender環境の両方で動作するようにしてください。

環境変数を利用してください。

少なくとも以下をRenderで利用できるようにしてください。

```text
SECRET_KEY
DATABASE_URL
DEBUG
RENDER_EXTERNAL_HOSTNAME
```

### SECRET_KEY

コードへ直接記述しないでください。

Renderの環境変数から取得してください。

---

### DEBUG

Renderでは必ず以下となるようにしてください。

```text
DEBUG=False
```

ローカル開発環境の挙動は壊さないでください。

---

### ALLOWED_HOSTS

Renderが自動提供する

```text
RENDER_EXTERNAL_HOSTNAME
```

を利用できるようにしてください。

ローカル開発の

```text
localhost
127.0.0.1
```

も必要に応じて維持してください。

---

### CSRF_TRUSTED_ORIGINS

RenderのHTTPS URLからPOST処理を行えるよう設定してください。

Renderホスト名から安全に生成する形を優先してください。

ホスト名をコードへ固定しないでください。

---

## 3. PostgreSQL

Renderでは

```text
DATABASE_URL
```

を利用してPostgreSQLへ接続してください。

ローカルDocker Composeで使用している既存PostgreSQL設定は壊さないでください。

Render環境では `DATABASE_URL` が存在する場合にRender PostgreSQLを使用し、それ以外では既存のローカル設定を利用するようにしてください。

---

# 4. static files

RenderではNginxを使用しないためWhiteNoiseを利用してください。

`settings.py` の `MIDDLEWARE` を確認し、

```text
SecurityMiddleware
↓
WhiteNoiseMiddleware
```

の順になるよう適切に設定してください。

また、

```text
STATIC_ROOT
```

を設定してください。

`collectstatic` がRenderのビルド時に正常実行できるようにしてください。

既存のCSS / JavaScript / 画像表示を壊さないでください。

---

# 5. media files

現在の画像アップロード・mediaファイルの実装を確認してください。

Render Free Web Serviceのローカルファイルシステムは永続化されないため、ユーザーや管理画面からアップロードしたファイルをRenderローカルへ永続保存する設計にはしないでください。

今回の一時公開で画像アップロード機能を利用している場合は、

* 現在どのように保存しているか
* Render無料環境で問題になるか
* 一時公開時にどの制限が発生するか

を調査してください。

勝手にS3やCloudinaryなどの外部有料サービスを追加しないでください。

リポジトリ内に存在するstatic画像については、通常どおり表示できるようにしてください。

---

# 6. build.sh

プロジェクトルートへRender用の

```text
build.sh
```

を作成してください。

最低限以下を実行してください。

```bash
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate
```

現在のプロジェクト構成を確認し、必要なら調整してください。

Render無料Web Serviceでは有料Web Service向けのpre-deploy機能を前提とせず、無料枠で動作する構成にしてください。

---

# 7. Gunicorn

RenderではGunicornからDjangoを起動してください。

Djangoプロジェクト名を実際のコードから確認してください。

想定が `config` の場合は、

```bash
gunicorn config.wsgi:application
```

ですが、必ず実際の `wsgi.py` の位置を確認して設定してください。

Renderから渡されるPORTで正常にWeb Serviceとして起動できることも確認してください。

---

# 8. render.yaml

プロジェクトルートへ

```text
render.yaml
```

を作成してください。

Render Blueprintから、

* Django Web Service
* PostgreSQL

をまとめて作成できる構成にしてください。

どちらも必ず無料プランを指定してください。

概念的には以下の構成です。

```yaml
databases:
  - name: yakugaku-quiz-db
    plan: free

services:
  - type: web
    name: yakugaku-quiz
    runtime: python
    plan: free
    buildCommand: ./build.sh
    startCommand: gunicorn config.wsgi:application

    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: yakugaku-quiz-db
          property: connectionString

      - key: SECRET_KEY
        generateValue: true

      - key: DEBUG
        value: "False"
```

ただし、このYAMLをそのまま使用するのではなく、現在のプロジェクト構成および最新のRender Blueprint仕様に合わせて修正してください。

Pythonバージョンについても、現在のプロジェクトのPython 3.12系と整合するようにしてください。

---

# 9. .gitignore

以下のような機密情報がGitへコミットされないことを確認してください。

```text
.env
.env.*
```

ただし、

```text
.env.example
```

など公開用テンプレートが存在する場合は維持してください。

SECRET_KEY、DBパスワードなどを絶対にGitへ追加しないでください。

---

# 10. メール機能

現在パスワード再設定等でメール送信機能を使用しているため、現在のメール設定を確認してください。

Render Free Web Serviceでは一般的なSMTPポートに制限があるため、SMTPを利用したメール送信を勝手に本番化しないでください。

今回は一時公開が目的なので、

* 現在のメール設定
* Render無料環境で利用できるか
* 利用できない場合にどの機能へ影響するか

を確認して報告してください。

外部メールサービスは勝手に追加しないでください。

---

# 11. DB初期データ

Render PostgreSQLは新規DBとなるため、既存のローカルDBデータが自動的に移行されるわけではありません。

現在のプロジェクト内に、

* fixture
* CSVインポート
* management command
* 初期データ投入処理

が存在するか確認してください。

存在する場合は、一時公開環境へ安全にデータ投入する方法を整理してください。

自動デプロイのたびに問題データが重複登録されるような処理は追加しないでください。

既存データを勝手に削除しないでください。

---

# 12. テスト

変更後、可能な範囲で以下を確認してください。

```bash
python manage.py check
```

```bash
python manage.py test
```

また、Render相当の

```text
DEBUG=False
```

でもDjangoのsystem checkが通るか確認してください。

可能であればGunicornからアプリケーションを起動し、起動エラーがないことも確認してください。

---

# 13. 既存機能確認

少なくとも以下に影響がないことを確認してください。

* トップページ
* ログイン
* 新規登録
* ログアウト
* マイページ
* クイズ
* 問題回答
* 解説表示
* 管理画面
* お知らせ
* staticファイル
* 問題画像

Render対応とは無関係なUI変更・機能変更は行わないでください。

---

# 14. ドキュメント

必要であれば

```text
docs/deploy/render.md
```

を作成してください。

以下を記載してください。

1. Renderへのデプロイ方法
2. Blueprintの作成方法
3. 必要な環境変数
4. Render URLへのアクセス方法
5. PostgreSQLについて
6. migrateについて
7. 初期データ投入方法
8. Render無料枠の制限
9. 一時公開終了後の削除方法
10. AWS環境とは独立した一時公開構成であること

---

# 制約

以下は禁止します。

* AWS向け設定の削除
* Dockerfileの削除
* docker-compose.ymlの削除
* Nginx設定の削除
* DB設計変更
* モデル変更
* UIデザイン変更
* 不要なリファクタリング
* 有料Renderサービスの利用
* SECRET_KEY等のGitコミット
* 外部サービスの独断追加

Render対応に必要な最小限の変更のみ実施してください。

---

# 作業完了時

チャットへの報告は簡潔にしてください。

以下だけ報告してください。

```text
Render一時公開対応完了

変更:
- xxx
- xxx
- xxx

確認:
- Django check: OK / NG
- Test: OK / NG

Render側で必要な作業:
1. xxx
2. xxx
3. xxx

注意点:
- xxx
```

詳細については作成したドキュメントへ記載してください。
