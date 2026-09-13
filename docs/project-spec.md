# yakugaku-quiz 仕様書 & プロジェクトガイド

薬剤師国家試験対策向けの Django 製クイズWebアプリケーションの仕様書および開発ガイドラインです。

---

## 1. プロジェクト概要

- **名称**: yakugaku-quiz（薬剤師国家試験対策クイズ）
- **目的**: 薬剤師国家試験の過去問・演習問題をスキマ時間で手軽に学習できるクイズ形式のWebサービス。
- **ターゲット**: 薬学部生・薬剤師国家試験受験生

---

## 2. 技術スタック・インフラ構成

### 2.1 アプリケーション技術スタック
| 区分 | 技術 | バージョン/備考 |
|---|---|---|
| 言語 | Python | 3.12 |
| フレームワーク | Django | 5.x / 6.x系 |
| データベース | PostgreSQL | 15 |
| Web/APサーバー | Gunicorn + Nginx | Dockerコンテナ |
| コンテナ環境 | Docker / Docker Compose | |
| フロントエンド | HTML5, Vanilla JavaScript, CSS | |
| 認証 | Django標準認証 (`django.contrib.auth`) | セッション認証 |

### 2.2 AWSインフラ構成（低コスト学習構成）

月額3,000円以内を目標としつつ、EC2とRDSを分離し、Route 53・CloudFront・S3を利用してAWSの主要サービスを学べる構成です。

高可用性よりもコストと学習を優先し、EC2とRDSは指定時間だけ起動します。本格公開時は、24時間稼働やALB・Auto Scaling・Multi-AZの追加を改めて検討します。

#### 構成概要

```text
ユーザー
  ↓
Route 53
  ↓
CloudFront
  ├── /static/*・/media/* → S3
  └── その他              → EC2
                                 ↓
                          RDS for PostgreSQL
```

#### 使用サービス

| サービス名 | 役割 / 設定内容 |
|---|---|
| **Amazon Route 53** | 独自ドメインの名前解決。公開用ドメインをCloudFrontへ向ける。 |
| **Amazon CloudFront** | Webサイトの入口。HTTPS対応、静的ファイルのキャッシュ、EC2への動的リクエスト転送を担当する。 |
| **AWS Certificate Manager (ACM)** | CloudFrontで使用するSSL/TLS証明書を管理する。CloudFront用証明書はバージニア北部 (`us-east-1`) で作成する。 |
| **Amazon S3** | CSS、JavaScript、画像などの静的・メディアファイルを保存する。バケットは非公開とし、CloudFrontからのみ参照させる。 |
| **Amazon EC2** (`t4g.micro`) | Django、Gunicorn、NginxをDocker Composeで稼働する。パブリックサブネットに1台だけ配置する。 |
| **Amazon RDS for PostgreSQL** (`db.t4g.micro`) | PostgreSQL 15、Single-AZ。プライベートDBサブネットに配置し、EC2からのみ接続を許可する。 |
| **Amazon EventBridge Scheduler** | EC2とRDSを平日の指定時刻に自動起動・停止する。 |
| **AWS Lambda** | EventBridge Schedulerから呼び出し、RDSとEC2の起動・停止、必要に応じてRoute 53レコード更新を実行する。 |
| **Amazon CloudWatch** | EC2・RDSの基本メトリクスと異常を監視する。ログ保存量は必要最小限にする。 |
| **AWS Systems Manager Parameter Store** | `SECRET_KEY`、DB接続情報などの機密情報を管理する。 |

#### 稼働スケジュール

- 原則として平日10:00〜22:00（日本時間）のみ稼働する。
- 起動時はRDSを先に起動し、利用可能になった後にEC2を起動する。
- 停止時はEC2を先に停止し、その後RDSを停止する。
- 土日・祝日は原則停止し、必要な場合のみ手動で起動する。
- 本格公開に移行するまでは、停止時間中にサービスを利用できないことを許容する。
- TerraformではSchedulerが5分ごとに状態を確認し、10:00からRDSの起動を開始する。起動完了とDNS反映までの待ち時間を許容する。
- 祝日・振替休日は`holiday_dates`で年ごとに管理する。`holiday_calendar_year`が当年と一致しない場合は自動起動を止め、ログにエラーを記録する。
- Terraformの設定・移行・再実行手順は`terraform/README.md`を参照する。

#### ネットワーク構成

- **VPC**: 1 VPC
- **パブリックサブネット**: EC2を配置
- **プライベートDBサブネット**: RDS用に異なるAZのサブネットを2つ用意
- **Internet Gateway**: EC2のインターネット接続に使用
- **NAT Gateway**: コスト削減のため使用しない
- **Application Load Balancer**: EC2が1台のため使用しない
- **Elastic IP**: 固定費削減のため使用しない

EC2の停止・起動でPublic IPv4アドレスが変更された場合は、起動処理でRoute 53のオリジン用Aレコードを更新します。CloudFrontのオリジンにはEC2のIPアドレスではなく、`origin.<domain>`形式のドメインを指定します。

#### CloudFrontキャッシュ方針

| パス | オリジン | キャッシュ |
|---|---|---|
| `/static/*` | S3 | 有効 |
| `/media/*` | S3 | 有効 |
| `/*` | EC2 | 無効 |

ログイン状態、セッションCookie、CSRFトークン、回答結果、学習履歴などを含む動的ページはキャッシュしません。

#### セキュリティグループ

- **EC2-SG**:
  - HTTP/HTTPSはCloudFrontからの通信に限定する。
  - SSHの22番ポートは原則公開しない。
  - Gunicornの待受ポートは外部公開しない。
- **RDS-SG**:
  - 5432番ポートを`EC2-SG`からのみ許可する。
  - Public accessは無効にする。

#### 機密情報

- `SECRET_KEY`、DB接続情報などをコードへハードコードしない。
- `.env`をGitへコミットしない。
- EC2からAWSサービスへアクセスする場合は、アクセスキーではなくIAMロールを優先する。
- IAMポリシーは最小権限とする。

#### バックアップ

- RDSの自動バックアップを有効にする。
- 保持期間は復旧要件と料金を確認して決定する。
- アプリケーションコードはGitで管理する。
- 大きな変更前には必要に応じてEBSスナップショットを作成する。

#### 料金方針

- AWS利用料は月額3,000円以内を目標とする。
- AWS Budgetsで1,500円、2,000円、2,500円相当の通知を設定する。
- AWS Budgetsは通知機能であり、料金を自動停止する仕組みではない点に注意する。
- 料金が増加する可能性のある構成変更は、実装前にユーザーへ確認する。

以下のサービス・構成は、ユーザーの明示的な承認なく追加しません。

- NAT Gateway
- Application Load Balancer
- 2台目以降のEC2
- RDS Multi-AZ
- Elastic IP
- AWS WAF
- 常時稼働への変更

#### 将来の拡張

アクセス数や可用性要件が高くなった場合は、次の順番で再検討します。

1. EC2・RDSの24時間稼働
2. EC2のインスタンスタイプ変更
3. Application Load Balancerの追加
4. Auto Scaling Groupと複数EC2の追加
5. RDS Multi-AZ化
6. NAT GatewayまたはVPCエンドポイントの追加

---

## 3. ディレクトリ構成

```text
yakugaku-quiz/
├── config/              # Djangoプロジェクト設定 (settings.py, urls.py, wsgi.py)
├── accounts/            # ユーザー認証・マイページ・トップページ
│   ├── views.py         # home, mypage, signup
│   └── ...
├── quiz/                # クイズ機能・問題出題・回答履歴ロジック
│   ├── models.py        # Question, Answer
│   ├── views.py         # question_view
│   └── admin.py         # 管理画面定義
├── templates/           # HTMLテンプレート
│   ├── home.html        # トップページ
│   ├── mypage.html      # マイページ（学習状況確認）
│   ├── quiz/
│   │   └── question.html # クイズ画面（出題・回答・結果・解説）
│   └── registration/    # 認証関連（login.html, signup.html など）
├── Dockerfile           # Webアプリ用コンテナ定義
├── docker-compose.yml   # PostgreSQL + Djangoの構成定義
├── requirements.txt     # Python依存パッケージ
├── manage.py            # Django管理スクリプト
└── README.md            # 一般向け説明書
```

---

## 4. データモデル設計 (ER仕様)

### 4.1 Question (問題テーブル)

出題される問題のマスターデータです。

| フィールド名 | 型 | 制約 / 選択肢 | 説明 |
|---|---|---|---|
| `id` | BigAutoField | PK | 問題ID |
| `question_code` | CharField(50) | UNIQUE、NULL/空欄許容 | CSVで必須の問題管理番号。既存問題は未設定可 |
| `text` | TextField | NOT NULL | 問題文 |
| `choice1` | CharField(255) | NOT NULL | 選択肢1 |
| `choice2` | CharField(255) | NOT NULL | 選択肢2 |
| `choice3` | CharField(255) | NOT NULL | 選択肢3 |
| `choice4` | CharField(255) | NOT NULL | 選択肢4 |
| `choice5` | CharField(255) | 空欄可、既定値 `''` | 選択肢5 |
| `choice6` | CharField(255) | 空欄可、既定値 `''` | 選択肢6 |
| `correct` | CharField(10) | NOT NULL | 正解番号（1〜6の文字列、空欄の選択肢は指定不可）。単一正解なら `'1'`、複数正解なら `'13'` のように連結して保持 |
| `explanation` | TextField | NOT NULL | 解答・解説文 |
| `category` | CharField(50) | 選択肢あり | 出題分野（下記参照） |
| `question_type` | CharField(20) | デフォルト `'general'` | 問題種別（下記参照） |

#### category の選択肢:
- `physics_chemistry_biology`: 物理・化学・生物
- `hygiene`: 衛生
- `pharmacology`: 薬理
- `pharmaceutics`: 薬剤
- `pathology`: 病態・薬物治療
- `law_ethics`: 法規・制度・倫理
- `practice`: 実務

#### question_type の選択肢:
- `required`: 必須問題（単一選択 / 1つのみ回答）
- `general`: 一般問題（複数選択 / 最大2つ選択）

---

### 4.2 Answer (回答履歴テーブル)

ユーザーごとの各問題への回答ログです。

| フィールド名 | 型 | リレーション / 説明 |
|---|---|---|
| `id` | BigAutoField | PK |
| `user` | ForeignKey(User) | 回答したユーザー (`CASCADE` 削除) |
| `question` | ForeignKey(Question) | 対象の問題 (`CASCADE` 削除) |
| `selected` | IntegerField / CharField | 選択した番号（文字列 `'13'` や整数値） |
| `is_correct` | BooleanField | 正解なら `True`、不正解なら `False` |
| `created_at` | DateTimeField | 回答日時 (`auto_now_add=True`) |

---

## 5. 機能一覧 & 画面仕様

### 5.1 ユーザー認証機能 (`/accounts/`)
- **新規登録 (`/accounts/signup/`)**: `UserCreationForm` を継承したフォームでユーザー名・メールアドレス・パスワードを登録。メールアドレスは再設定用として必須。登録後は完了案内付きでログイン画面へリダイレクト。
- **ログイン (`/accounts/login/`)**: Django標準のログイン画面。
- **ログアウト (`/accounts/logout/`)**: POSTリクエストによるセーフログアウト。
- **パスワード再設定 (`/accounts/password_reset/`)**: 登録メールアドレスに再設定リンクを送信し、新しいパスワードを設定。無効・使用済みリンクには再送信導線を表示。開発環境ではメールをコンソール出力。
- 認証画面は共通ヘッダー・フッター付きのレスポンシブ表示。入力エラーは日本語で表示。

### 5.2 トップ画面 (`/`)
- ログイン状況に応じた分岐表示。
- 未ログイン: ログイン / 新規登録 リンク
- ログイン中: 挨拶、クイズ開始リンク、マイページリンク、ログアウトボタン

### 5.3 クイズ画面 (`/quiz/`)
出題・回答・結果確認・解説閲覧を1画面で完結して行います。

1. **出題ロジック (GET)**:
   - **モード選択**: 通常モード / 苦手問題モード (`mode=weak`)
     - *苦手問題の判定条件*: 回答回数 $\ge 2$ かつ 正答率 $< 50\%$ の問題を抽出
   - **フィルタリング**:
     - 分野フィルタ (`category`)
     - 種別フィルタ (`question_type` / 必須・一般)
   - **連続出題防止**: 前問のIDをセッション (`last_question_id`) に保持し、直前と同じ問題が連続で出題されるのを防止。
   - **ランダム選出**: 絞り込まれた問題セットから `random.choice` で1問抽出。

2. **解答UI (フロントエンド)**:
   - choice1〜choice6のうち値がある選択肢のみ番号を保って表示。既存4択、5択、6択に対応。
   - **必須問題 (`required`)**: ラジオボタン（単一選択）
   - **一般問題 (`general`)**: チェックボックス（複数選択）。JavaScriptにより **最大2つまで** しか選択できないよう制限。

3. **採点・履歴保存 (POST)**:
   - 選択された選択肢（リスト）と問題の正解文字列を順不同で照合比較 (`sorted(selected) == sorted(correct_answers)`)。
   - 正誤判定結果 (`is_correct`) と回答内容を `Answer` レコードとして保存。
   - 回答後は「解答結果」として正解 / 不正解を先頭に大きく表示し、結果見出しへフォーカス・スクロールする。あなたの回答、正解テキスト、解説の順に表示。問題文・選択肢は解説の下に折りたたまず常時表示する。
   - 「次の問題へ」ボタンで同一条件の次の問題を取得。

4. **画面・操作**:
   - 共通ヘッダー付きのレスポンシブ画面で問題・選択肢・正誤・正解・解説を表示。
   - 未選択、不正な値（空欄の選択肢への回答を含む）、選択数超過はサーバーでも検証し、履歴を保存しない。
   - 次問・スキップ・再挑戦でも科目、問題種別、モードを維持。
   - ブックマークはCSRF対策付きPOSTでセッションに保存（同一ブラウザのセッション内）。
   - 指定問題数は1〜100問、未指定はセッション設定または30問。指定数の回答後に完了案内を表示。スキップは回答数に含めない。

5. **学習進捗表示**:
   - ユーザーの通算正答率（正解数 / 総回答数）を画面上にリアルタイム表示。

### 5.4 マイページ (`/mypage/`)
ログインが必要です。未ログイン時はログイン画面へ移動し、認証後に戻ります。ユーザーの学習成果・統計情報を確認できます。
- 累計回答数 (`total`)
- 累計正解数 (`correct`)
- 全体正答率 (`accuracy` %)
- 苦手問題数 (`weak_count` : 2回以上回答し、正答率50%未満の問題数)
- 基本情報（ユーザー名・メールアドレス）、パスワード再設定へのリンク
- 連続学習日数（日本時間で今日または昨日から連続する回答日数。同日の複数回答は1日）
- 科目別進捗（回答済みの異なる問題数 / 科目の全問題数）と科目別正答率。物理・化学・生物はデータモデルに合わせて1科目として表示
- 問題演習・苦手復習・お知らせへの導線。回答がない場合は未学習の案内を表示

### 5.5 お知らせ
- 一覧 (`/news/`): 公開日時の新しい順に10件ずつ表示。お知らせがない場合は案内を表示。
- 詳細 (`/news/<id>/`): タイトル・公開日時・本文を表示。本文はプレーンテキストで、改行を保持してHTMLをエスケープ。
- 公開条件: `is_published=True` かつ公開日時が現在以前。下書き・公開前の記事は詳細URLでも404。
- トップとマイページに最新3件を表示。ヘッダーから一覧へ移動可能。
- `accounts.News`: タイトル（200文字）、本文、公開フラグ（初期値は非公開）、公開日時、作成日時、更新日時。
- 管理画面から追加・編集・削除、タイトル・本文検索、公開状態・日時の絞り込みが可能。未来の公開日時を設定すると予約公開。

### 5.6 管理画面 (`/admin/`)
- 問題（`Question`）の追加・編集・削除
- Question一覧のインポートからUTF-8（BOM付き可）のCSVをアップロードし、プレビュー確認後に一括登録・更新。`question_code`をキーに更新し、重複・入力エラー時は全件ロールバックする。追加・変更権限が必要。
- CSV形式・入力条件は[問題CSVインポート仕様](product-specs/question-csv-import.md)、サンプルは[こちら](features/samples/questions-import-sample.csv)を参照。
- 回答ログ（`Answer`）の閲覧・管理

---

## 6. URLルーティング一覧

| パス | ビュー / アプリ | 役割 |
|---|---|---|
| `/` | `accounts.views.home` | トップページ |
| `/quiz/` | `quiz.views.question_view` | クイズ出題・回答・解説画面 |
| `/mypage/` | `accounts.views.mypage` | 学習データ・統計マイページ |
| `/accounts/signup/` | `accounts.views.signup` | 新規会員登録 |
| `/accounts/login/` | `django.contrib.auth.views.LoginView` | ログイン |
| `/accounts/logout/` | `django.contrib.auth.views.LogoutView` | ログアウト |
| `/admin/` | `django.contrib.admin.site.urls` | Django管理画面 |

---

## 7. 開発・実行手順

### 起動 (Docker Compose)
```bash
# ビルド & 起動
docker compose up -d --build

# マイグレーション
docker compose exec web python manage.py migrate

# 管理ユーザー作成
docker compose exec web python manage.py createsuperuser

# テスト実行
docker compose exec web python manage.py test
```

---

## 8. 今後の拡張・改善予定 (TODO)

- [ ] **UI/UX向上**: Bootstrap / TailwindCSS または洗練されたVanilla CSSによるモダンで使いやすいデザイン適用
- [ ] **マイページの充実**: 分野別（薬理、薬剤など）の正答率グラフ表示、苦手問題一覧リスト
- [ ] **問題データインポート**: CSV / JSON 形式での問題一括インポートコマンド (`management/commands`)
- [ ] **制限時間機能 / 模試モード**: 実際の国試形式（必須90問、一般問題など）の通し演習モード

---
