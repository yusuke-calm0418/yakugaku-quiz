# Renderへの一時公開

AWS本番構成とは独立した、一時確認用の構成です。Python 3.12、Gunicorn、WhiteNoise、PostgreSQL 15を使用します。Dockerfile / Docker Compose / Terraformとローカル開発の起動方法は変更していません。Nginxを新設・削除する変更もありません。

## 1. デプロイ

1. 今回の変更をGitリポジトリへコミット・pushします。`static/css/style.css` も必ず含めてください。これは従来Git管理外だった既存CSSで、内容を変更せず公開に含めています。`static/scss/style.scss` とは内容が異なるため、ビルド時の再生成は行いません。
2. Renderの無料ワークスペースで **New → Blueprint** を選び、リポジトリと公開対象ブランチを指定します。Blueprint Pathはルートの `render.yaml` です。
3. 新規の `yakugaku-quiz` と `yakugaku-quiz-db` が両方 **Free**、リージョンが両方Singaporeであることを確認して作成します。同名の既存サービスがある場合は、意図せず設定を上書きしないようYAMLのサービス名・DB名・`fromDatabase.name`を変更します。
4. Web Serviceのログでビルド・migrate・Gunicorn起動の成功を確認します。Dashboardに表示された `https://<サービスのホスト名>.onrender.com/` へアクセスします。管理画面は同じURLの `/admin/` です。

無料プランを明示する理由や設定項目は[Render Blueprint仕様](https://render.com/docs/blueprint-spec)を参照してください。無料DBがすでにあるワークスペースでは追加作成できません。有料プランへの変更で回避しないでください。

## 2. 環境変数・起動

| 変数 | 設定方法・用途 |
| --- | --- |
| `SECRET_KEY` | Blueprintがランダム生成。環境変数から取得し、`DEBUG=False`で未設定なら起動エラーにします。コードやGitへ保存しません。 |
| `DATABASE_URL` | BlueprintがDBのInternal Database URLを設定します。接続先をログやチャットに貼らないでください。 |
| `DEBUG` | Blueprintでは文字列 `False`。Renderの環境変数を検出した場合は、誤ってTrueを指定してもFalseを維持します。 |
| `RENDER` | Render自動設定の `true`。Render固有設定の判定に使用します。 |
| `RENDER_EXTERNAL_HOSTNAME` | Render自動設定。許可ホストと `https://` のCSRF信頼元に追加します。手動で固定しません。 |
| `PORT` | Render自動設定。Gunicornが `0.0.0.0:$PORT` で待ち受けます。 |
| `ALLOWED_HOSTS` | 任意のカンマ区切りホスト名。通常は不要です。Renderの自動ホストは別途追加されます。 |
| `EMAIL_PROVIDER` | 実配送は `resend`。未設定時は `console` でログ出力のみ。新規登録のメール確認を一般利用者に提供する前に設定してください。 |
| `RESEND_API_KEY` | Resendの送信専用APIキー。RenderのEnvironmentに秘密値として設定し、コード・Git・ログに出しません。 |
| `DEFAULT_FROM_EMAIL` | Resendで許可された送信元アドレス。`resend` 使用時は必須。送信元の条件は下記「メール配送」を参照してください。 |
| `SITE_URL` | 確認メールのURLに使うorigin（末尾パスなし）。Renderでは `https://<サービスのホスト名>.onrender.com`。未指定時は `RENDER_EXTERNAL_HOSTNAME` から生成します。 |
| `EMAIL_VERIFICATION_TIMEOUT` | 任意。確認URLの有効秒数。既定86400（24時間）。 |
| `EMAIL_VERIFICATION_RESEND_INTERVAL` | 任意。同一ユーザーへの送信試行間隔の秒数。既定60。送信失敗も対象。 |

Pythonは[Renderが対応する `.python-version`](https://render.com/docs/python-version)で3.12系を指定しています。Dashboardに既存の `PYTHON_VERSION` があればそちらが優先されるので、削除するか3.12系の完全なバージョンと整合させてください。

RenderではHTTPSのプロキシヘッダーを認識し、セッション・CSRF CookieをSecureにします。HTTPS終端・HTTPからHTTPSへの転送はRender側を利用します。WhiteNoiseはSecurityMiddlewareの直後に入り、`staticfiles/` のCSS・JavaScript・static画像を圧縮配信します。既存のstatic URLを維持するため `CompressedStaticFilesStorage` を使用します。

ローカルでは従来のPostgreSQL接続設定と `DEBUG=True` が既定です。`DATABASE_URL` がある場合のみURLの接続先を優先します。ローカルの秘密鍵が未指定なら実行時に生成し、runserverの自動リロードには引き継ぎますが、コンテナ再起動後はセッションが無効になります。固定が必要なら環境変数 `SECRET_KEY` を渡してください。`.env` の自動読み込みは追加していません。ローカル環境にはRenderの接続情報を常設しないでください。

## 3. ビルド・マイグレーション

`bash build.sh` は順番に以下を実行し、失敗時は停止します。

1. `python -m pip install -r requirements.txt`
2. `python manage.py collectstatic --no-input`
3. `python manage.py migrate --no-input`

無料枠で使えないpre-deploy機能や有料ジョブを使いません。migrateはビルド中にDBへ適用されるため、後続のデプロイに失敗しても適用済みmigrationは戻りません。認証改修では `accounts/0002_emailverification` が確認状態用テーブルを追加します。標準auth_userへのUNIQUE制約追加、既存Userの書換え・削除・一括無効化はありません。問題や管理ユーザーの自動投入、データ削除処理は追加していません。

## 4. 管理ユーザー・初期データ

新規Render DBはローカルDBとは別で、問題・ユーザー・回答履歴・お知らせは自動移行されません。既存リポジトリには初期データfixture、独自management command、データ投入migrationはなく、管理画面のCSVインポートとサンプルCSVがあります。

無料Web ServiceにはDashboard Shell / SSH / one-off jobがありません。管理者作成には、ローカルのDjangoからRender DBへ一時接続します。

1. ローカルの依存関係を更新します: `docker compose build web`、`docker compose up -d web`。
2. Render DBの **Networking / Access Control** で、作業端末の公開IPだけを `/32` で一時許可します。Blueprintの `ipAllowList: []` は外部接続を閉じています。全IP許可にしないでください。Render Webからの内部接続には影響しません。
3. DBの **External Database URL** を確認し、次のコマンドの非表示入力へ貼り付けます。URLをコマンドに直接書きません。migrateはRenderのビルドで完了していることを確認してください。

```bash
docker compose exec web python -B -c '
import getpass
import os
import secrets
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

parts = urlsplit(getpass.getpass("Render External Database URL: "))
if parts.scheme not in ("postgres", "postgresql") or not parts.hostname:
    raise SystemExit("PostgreSQLのExternal Database URLを入力してください。")
query = dict(parse_qsl(parts.query))
query["sslmode"] = "require"
os.environ["DATABASE_URL"] = urlunsplit(parts._replace(query=urlencode(query)))
os.environ["DEBUG"] = "False"
os.environ["SECRET_KEY"] = secrets.token_urlsafe(64)
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
from django.core.management import execute_from_command_line
execute_from_command_line(["manage.py", "createsuperuser"])
'
```

この秘密鍵はローカルで管理コマンドを起動するためだけの一時値です。Renderの秘密鍵をコピーする必要はありません。接続情報はこのプロセスのみに設定され、既存ローカルDBやコンテナ設定を書き換えません。

4. 完了後すぐDBの外部許可IPを削除し、外部アクセスを閉じます。
5. Renderの `/admin/` にログインし、Question一覧のインポートからCSVをアップロードします。プレビューで確認した後に確定してください。[CSV仕様](../product-specs/question-csv-import.md)と[サンプル](../features/samples/questions-import-sample.csv)を参照してください。`question_code` による更新なので同じコードを再投入しても重複しませんが、既存内容は更新されます。
6. お知らせは管理画面で必要なものだけ登録します。利用者は通常の新規登録から作成できます。

CSVプレビューの一時ファイルは消える場合があるため、確認中に再デプロイ・休止が起きた場合は最初からアップロードし直してください。ローカルDB全体のdumpを無条件に取り込む手順は採用していません。

## 5. 画像の制限とメール配送

- 問題画像は既存の `ImageField` が `media/questions/` に保存します。Git対象外であり、ローカルで登録した画像はRenderへ移りません。
- Render無料環境のファイルは再起動・再デプロイ・休止で失われ、永続ディスクを付けられません。また、既存のmedia配信URLは `DEBUG=True` の場合だけ有効です。**今回のRender公開では問題画像のアップロード・配信を利用しません。画像を必要としない問題を投入してください。** 管理画面の既存画像欄を使用しても永続化・配信はできません。
- ローカルの問題画像登録・表示は従来どおりです。static内のロゴ・背景・トップ画像はWhiteNoiseで配信されます。S3等の外部ストレージは追加していません。
- メール配送はローカルのconsole出力と、RenderのResend HTTP APIを切り替えます。メール確認とパスワード再設定の両方がDjango Mail APIを使います。
- Free Web ServiceのSMTP制限を避けるため、ResendへはAnymailのBackendを通じてHTTPSで接続します。SMTP接続やWebhookは追加していません。

これらのサービス側制限は[Render無料枠の公式説明](https://render.com/docs/free)を参照してください。

### Resend設定・実配送の確認

1. Resendで送信元を準備します。一般利用者へ送るには、自分がDNSを管理できるドメインをResendで認証し、そのドメインの送信元を `DEFAULT_FROM_EMAIL` に指定します。WebアプリのURLはRenderのURLのままで構いません。`onrender.com` 自体を自分の送信元ドメインとして認証することはできません。
2. 独自ドメインが未準備の場合、Resendのテスト用送信元 `onboarding@resend.dev` はResendアカウント所有者のメール宛のテストに限られます。任意の新規登録者には送れません。[Resendの送信元制限](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain)を参照してください。
3. 送信専用（Sending access）のAPIキーを作成し、Render Environmentに `EMAIL_PROVIDER=resend`、`RESEND_API_KEY`、`DEFAULT_FROM_EMAIL` を設定します。必要なら `SITE_URL` に公開originを設定して再デプロイします。APIキー・送信元が欠けたResend設定は起動時エラーになります。設定方法は[AnymailのResend設定](https://anymail.dev/en/stable/esps/resend/)に基づきます。
4. テスト受信者本人が新規登録します。届いた確認URLを開く前はログインできず、開いた後にメール＋パスワードでログインできることを確認します。確認済みURLを再度開いても安全に案内されます。
5. 未確認アカウントへの再送、60秒以内の抑止、パスワード再設定の実配送を確認します。メール未達時はResend Dashboardの配送状態と送信元・宛先制限を確認します。API受付成功は受信箱への到達を保証しません。

送信処理は最大10秒のHTTP timeoutを設定しています。登録時の送信失敗ではUserとEmailVerificationを未確認のまま保持し、再送導線を表示します。再送画面は未知・確認済み・停止済み・重複・送信失敗でも共通案内を返します。ログには例外の型だけを記録し、メール本文やAPIレスポンスを記録しません。Anymailの `DEBUG_API_REQUESTS` は有効化しないでください。console出力やWebアクセスログには確認リンクが含まれ得るため、ログの共有を避け、公開運用時のアクセスログ保存先・保持・URLマスキングも確認してください。

ローカルでは `docker compose logs web` のメール内リンクを開いて確認できます。`SITE_URL` の既定は `http://localhost:8000`。未設定の開発用SECRET_KEYはコンテナ再起動で変わるため、以前の確認リンクを利用する場合は固定SECRET_KEYを環境変数で管理してください。

### 既存ユーザー・AWS移行

既存activeユーザーは、一意なemailが設定されていれば確認管理レコードがなくてもメールログインできます。空・重複emailは自動修正しません。導入前に対象DBの該当データを管理者が確認し、必要な変更は本人と照合して実施してください。管理画面は既存のusername＋パスワードを維持します。

AWS本番ではAmazon SES API＋IAM Roleを想定します。独自ドメイン・SESドメイン認証/DKIM・Sandbox解除・IAM Role・SES用Anymail依存関係とBackend設定は将来対応です。`SITE_URL` も独自ドメインに変更し、許可Host・CSRF・HTTPS設定を移行先と整合させます。メール生成・確認token・登録/確認/再送フローは配送サービスに依存しません。今回AWSリソースの作成やSES実接続は行っていません。

## 6. 無料枠と公開終了

- 無通信15分でWebが休止し、再アクセス時の起動に待ち時間があります。Web稼働枠はワークスペース全体で月750時間です。
- 無料DBは1ワークスペースにつき1個、1GB、作成から30日で期限切れになります。期限切れ後は接続できず、その14日後に削除されます。無料DBにマネージドバックアップはありません。必要なデータの退避は期限前に実施してください。
- 帯域・ビルド時間にも枠があります。有料利用を避けるため支払い方法を登録しない無料ワークスペースを使用し、Billing / Usageを確認してください。支払い方法が既登録なら超過課金が発生し得るため、無料サービス指定だけでは無課金を保証できません。ビルドの追加支出上限も確認してください。
- 終了前に必要なデータが退避済みであることを確認してから、対象のWeb ServiceとPostgreSQLをDashboardで明示的に削除します。Blueprintだけの削除でリソースが消えたと判断せず、両方が削除されたことを確認します。DB削除でデータは失われます。AWS・ローカル環境は削除対象ではありません。

料金・期限・制限の最新値は[Render無料枠](https://render.com/docs/free)で確認してください。

## 7. 公開後の確認

トップ、メールログイン、新規登録→確認メール→確認完了、再送、パスワード再設定、POSTログアウト、マイページ、問題表示・回答・解説、管理画面、お知らせを確認します。ブラウザのNetworkで `/static/css/style.css`、`/static/styles/`、`/static/js/quiz.js`、`/static/js/auth.js`、`/static/images/` が200で取得できること、HTTPSからのPOSTがCSRFエラーにならないことを確認してください。パスワード欄ごとの表示切替も確認します。問題画像は上記の一時公開制限に従います。

## 8. Render一時公開構成の追加時点での検証結果（認証改修前）

既存Docker環境のPython 3.12 / PostgreSQL 15で以下を確認しました。

| 確認 | 結果 |
| --- | --- |
| `python manage.py check` | 通常設定・Render相当の `DEBUG=False` とも成功 |
| `python manage.py test --noinput` | 通常設定44件、Render相当設定44件とも成功 |
| `bash build.sh` | 分離した新規PostgreSQL DBで依存導入・static収集・全migration適用が成功 |
| Gunicorn | `config.wsgi:application` をPORT指定で起動し、公開ページ200・認証が必要なページのリダイレクトを確認 |
| static配信 | 共通CSS・各画面CSS・JS・画像・管理画面CSSの計12ファイルが200 |
| HTTPS / CSRF | Render相当ホストからのPOST受付、異なるOriginの403、Secure Cookieを確認 |
| 設定不備 | 秘密鍵未設定の公開モードは起動失敗、Renderで `DEBUG=True` を指定してもFalse、未知のHostは400 |
| ローカル互換 | URL未指定時の既存DB接続設定、問題画像登録・変更・クリア・開発配信を確認（既存テスト内） |
| 定義ファイル | build.shの構文、YAML構文、Web / DB両方のfree指定、Gitの機密情報除外を確認 |

検証用DBとGunicornプロセスは終了後に削除・停止済みです。既存のローカル業務データへの投入は行っていません。Renderアカウント上でのBlueprint作成・実デプロイ・Render PostgreSQLへの接続は未実施です。実サービスのURLでの最終確認は公開後に行ってください。

## 9. 認証改修の検証結果

2026-09-17、DockerのPython 3.12 / PostgreSQL 15で確認しました。

- 改修前の既存44テスト成功。改修後は全72テスト成功。Render相当（DEBUG=False、Resend設定）でも全72テスト成功。
- Django check、migration差分チェック（変更なし）、Docker再ビルド成功。`accounts.0002_emailverification` をローカルDBへ適用済み。標準Userのデータ変更migrationはありません。
- 再ビルド環境はDjango 6.1.1 / Anymail 15.2。accountsの既存AutoFieldを明示し、Djangoの既定主キー型変更による不要な既存テーブル変更を防いでいます。
- Resend BackendのHTTP通信をmockし、確認メール・再設定メールの送信先API、宛先、送信元、本文、HTTP失敗時の保留状態とログ秘匿を検証しました。実際のResendへの送信はしていません。
- `npm run sass`、JS構文確認、表示切替の独立動作・値の保持・ARIA状態・ページ復帰時の非表示化をNodeのDOM模擬環境で確認しました。ブラウザE2Eは未実施です。
- 起動中のローカルWebで、登録・ログイン・再送・無効確認リンク・auth.js・auth.cssの6URLが200を返すことを確認しました。

Renderへのデプロイ・環境変数登録・実メール受信確認、AWS本番への移行・SES実接続は未実施です。
