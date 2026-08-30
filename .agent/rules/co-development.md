# AIとエンジニアの共同開発ルール（Co-Development Guidelines）

このルールは、yakugaku-quiz プロジェクトにおいてAI（Antigravity等）とエンジニアがペアプログラミング・共同開発を進める際の行動指針および規約です。

---

## 1. コミュニケーション & 意思決定方針
- **独断での破壊的変更の禁止**: DBスキーマ変更、アーキテクチャの大幅な変更、主要機能の削除等は、事前に提案・合意を得てから着手する。
- **インクリメンタルな開発**: 大きな変更は一度に行わず、小さなタスク単位に分割して実装・検証を繰り返す。
- **設計意図の共有**: ライブラリの選定や実装パターンの採用にあたり、理由とトレードオフを明確に説明する。

---

## 2. 実装・コード品質規約 (Django / Python)
- **Django ベストプラクティス**:
  - ビジネスロジック・集計ロジックは Model / QuerySet / Service 層に集約し、Viewをスリムに保つ（Thin View）。
  - クエリ実行時の N+1 問題を避けるため、`select_related` / `prefetch_related` を適切に適用する。
- **可読性・型安全性**:
  - 主要な関数・メソッドには適切な Python Type Hint を付与する。
  - 不要なデバッグコード（`print` や不要なコメントアウト）はコミット前に除去する。
- **セキュリティ・機密情報保護**:
  - `SECRET_KEY`、DBパスワード、AWSアクセスキー等は絶対にコードにハードコードせず、`.env` や環境変数から読み込む。
  - SQLインジェクション、XSS、CSRF 脆弱性を防ぐため、Django の ORM やテンプレートエスケープを正しく活用する。

---

## 3. インフラ・デプロイ方針 (AWS パターンB)
- **AWS サービス構成**:
  - Web/APサーバー: Amazon EC2 (`t4g.small` / `t3.micro` + Docker / Gunicorn + Nginx)
  - DB: Amazon RDS for PostgreSQL (`db.t4g.micro`, プライベートサブネット配置)
  - ストレージ: Amazon S3 (`django-storages` + `boto3` による静的・メディア配信)
  - DNS: Amazon Route 53
  - SSL/TLS: Let's Encrypt / Certbot によるHTTPS化
- **ネットワーク分離**:
  - Webはパブリックサブネット、DBはプライベートサブネットに配置し、DBへのアクセスはEC2のセキュリティグループからのみ許可する。

---

## 4. テスト & ドキュメント管理
- **回帰テスト**: コード変更後は必ず `python manage.py test`（または `docker compose exec web python manage.py test`）を実行して既存動作を保証する。
- **テストのセット作成**: 新規エンドポイントやロジック作成時は単体・結合テストを作成する。
- **ドキュメント即時同期**: 仕様・モデル・インフラの変更時は、`.agent/AGENTS.md` および `README.md` を速やかに更新する。
