# 認証機能改修：メールログイン・メール確認・パスワード表示切替

## 1. 目的

既存の Django 製クイズアプリ `yakugaku-quiz` の認証機能を改修する。

今回実装する機能は以下。

1. メールアドレス + パスワードでログインできるようにする
2. 新規登録時に確認メールを送信する
3. メール内の確認URLを開いた後にアカウントを利用可能にする
4. 確認メールの再送機能を追加する
5. パスワード入力欄に表示 / 非表示切替を追加する
6. 既存のusername依存表示・メール・テストを必要に応じて修正する
7. ローカル・Render・将来のAWS本番環境でメール配送方式を切り替えられる構成にする
8. 実装内容を仕様書・デプロイ手順へ反映する

既存機能を壊さないことを最優先とする。

---

# 2. 作業前の確認

実装開始前に必ず以下を確認すること。

* `AGENTS.md`
* `docs/project-spec.md`
* `docs/agent/development.md`
* `docs/agent/design.md`
* `docs/agent/chat-output.md`

また、以下の既存コードを確認してから実装方針を確定すること。

* `accounts/forms.py`
* `accounts/views.py`
* `accounts/models.py`
* `accounts/tests.py`
* `config/settings.py`
* `config/urls.py`
* `templates/base.html`
* `templates/mypage.html`
* `templates/registration/base.html`
* `templates/registration/fields.html`
* `templates/registration/login.html`
* `templates/registration/signup.html`
* `templates/registration/password_reset_email.html`
* `static/scss/auth.scss`
* `static/styles/auth.css`
* `docs/project-spec.md`
* `docs/deploy/render.md`

既存実装を確認せず、大規模な書き換えを行わないこと。

---

# 3. 現在の認証仕様

現在は以下の構成。

* Python 3.12
* Django 5.x〜6.x
* PostgreSQL 15
* Django標準 `User` モデル
* `AUTH_USER_MODEL` 独自設定なし
* `AUTHENTICATION_BACKENDS` 独自設定なし
* `django-allauth` 等の外部認証ライブラリなし
* Django標準セッション認証
* ログインは `django.contrib.auth.urls` の標準 `LoginView`
* 現在のログインIDは `username`
* `SignupForm` は `UserCreationForm` を継承
* 現在の登録項目:

  * username
  * email
  * password1
  * password2
* emailはフォーム上必須
* DB上ではemailは一意ではない
* 登録時は `form.save()` 後、`is_active=True`
* 登録後はそのままログイン可能
* 登録確認メールなし
* メール確認URLなし
* 確認メール再送機能なし
* パスワード再設定はDjango標準機能で実装済み
* 開発環境の `EMAIL_BACKEND` は `console.EmailBackend`
* Render無料環境で仮公開中
* 将来的に独自ドメインを取得しAWSへ本番移行予定
* ヘッダー、マイページ、再設定メール、一部テストがusernameに依存
* パスワードフィールドは `templates/registration/fields.html` で共通出力
* 認証画面専用JavaScriptなし
* SCSSとコンパイル済みCSSを両方Git管理
* Sassは `npm run sass` でコンパイル

---

# 4. 今回の基本方針

## 4.1 Django標準Userを維持する

今回の改修ではカスタムUserモデルへ移行しない。

以下は変更しないこと。

```python
AUTH_USER_MODEL
```

また、原則としてアプリ全体の認証方式を変更する目的で

```python
AUTHENTICATION_BACKENDS
```

を独自Backendへ置き換えない。

既存DB・既存ユーザー・管理画面への影響を最小化するため、Django標準Userを維持する。

---

# 5. usernameの扱い

一般ユーザーには今後usernameを入力させない。

新規登録画面の項目は以下とする。

```text
メールアドレス
パスワード
パスワード確認
```

ただしDjango標準Userではusernameが必要なため、内部的には自動生成する。

例:

```text
user_6e46e176d78c44e894f3d6b90c4f42b8
```

UUID等を使用し、他ユーザーと重複しない値を生成すること。

この内部usernameは通常の画面・メールには表示しない。

---

# 6. 既存管理者ログインを維持する

Django Adminのログイン方法を壊してはいけない。

```text
/admin/
```

については、既存通り

```text
username + password
```

でログイン可能な状態を維持する。

そのため、アプリケーション全体を単純にemail専用AuthenticationBackendへ変更しないこと。

一般ユーザー向けログイン画面のみemailログインへ変更する。

---

# 7. メールアドレス正規化

メールアドレスは認証IDとして扱うため、登録・ログイン・再送処理で同一の正規化処理を使用する。

共通関数を用意すること。

例:

```python
normalize_email_address(email)
```

最低限以下を行う。

1. 前後空白を除去
2. 大文字小文字を統一
3. DB検索時も大文字小文字を区別しない

基本方針:

```python
email = email.strip().lower()
```

DB検索では必要に応じて

```python
email__iexact=email
```

を使用する。

Gmailの `.` や `+` 等を独自に削除するような、プロバイダ固有の正規化は行わないこと。

---

# 8. 既存ユーザーのメール問題

既存DBには以下が存在する可能性がある。

* emailが空
* emailが重複
* 大文字小文字のみ異なるemail
* 前後空白付きemail

これらを自動的に削除・統合・書き換えしないこと。

今回の実装では `auth_user.email` にDBレベルのUNIQUE制約を追加しない。

理由:

* 既存データとの競合リスクがある
* 既存ユーザーを破壊する可能性がある
* 標準Userテーブルへの影響が大きい

新規登録についてはアプリケーション側で

```python
User.objects.filter(email__iexact=email).exists()
```

等により重複を拒否する。

既存の重複メールについては、メールログイン時に複数ユーザーへ一致した場合、どれか1人を勝手に選択しない。

ログイン失敗として安全に処理する。

エラー内容から「登録ユーザーが何人存在するか」等を外部へ露出しないこと。

---

# 9. メールログイン

一般ユーザーのログイン画面を

```text
username + password
```

から

```text
email + password
```

へ変更する。

Django標準 `AuthenticationForm` をベースに専用フォームを作成することを優先する。

例:

```python
EmailAuthenticationForm
```

処理イメージ:

```text
入力email
↓
正規化
↓
User.emailをcase-insensitive検索
↓
一致するUserが1件のみ存在することを確認
↓
内部usernameを取得
↓
Django標準authenticate()へ渡す
↓
認証成功
```

Django標準認証機構を可能な限り利用する。

独自のパスワード照合処理は実装しない。

---

# 10. 既存ユーザーの扱い

既存ユーザーについては以下の条件を満たす場合、メールログイン可能とする。

* emailが設定されている
* 同一メールアドレスのユーザーが1人だけ
* `is_active=True`
* パスワードが正しい

今回追加するメール確認管理レコードを持たない既存ユーザーについては、既存ユーザーとして扱い、強制的にメール確認を要求しない。

既存ユーザーを今回のリリース時点で一括 `is_active=False` にしないこと。

---

# 11. メール確認状態の管理

`User.is_active` のみで

```text
メール未確認
管理者による停止
```

を区別しないこと。

確認済みユーザーを管理者が `is_active=False` にした場合に、確認メール再送等によって勝手に再有効化される問題を防ぐ。

そのため、メール確認状態を管理するモデルを追加する。

例:

```python
class EmailVerification(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

必要に応じて命名は既存コード規約に合わせて変更してよい。

目的は以下を区別すること。

```text
メール未確認
メール確認済み
管理者等によるis_active停止
```

既存ユーザーに対して自動でレコードを作成する必要はない。

新規登録ユーザーから管理対象とする。

---

# 12. 新規登録フロー

新規登録時は以下の順序とする。

```text
/signup/
   ↓
email / password入力
   ↓
email正規化
   ↓
重複確認
   ↓
User作成
   ↓
is_active=False
   ↓
EmailVerification作成
   ↓
確認メール送信
   ↓
「確認メールを送信しました」画面
```

登録直後にログイン可能にしてはいけない。

User保存時:

```python
user.is_active = False
```

とする。

---

# 13. 確認メール

確認メールにはメール確認用URLを含める。

例:

```text
https://example.com/accounts/verify-email/<token>/
```

Render仮公開中はRenderの公開URLを使用できること。

将来独自ドメインへ移行した際には、設定値の変更だけで独自ドメインURLへ切り替えられること。

URLをコードへ直接ハードコードしない。

トークンは

* 推測困難
* 改ざん検知可能
* 有効期限付き

とする。

Django標準機能を利用する。

推奨:

```python
django.core.signing
```

例:

```python
signing.dumps(...)
signing.loads(..., max_age=...)
```

専用saltを使用する。

例:

```text
accounts.email-verification
```

必要に応じてユーザーIDとemailをtokenへ含める。

発行後にユーザーのemailが変更されていた場合、古いtokenは無効とする。

---

# 14. 確認URLの有効期限

メール確認URLには有効期限を設定する。

設定値は `settings.py` に定義する。

例:

```python
EMAIL_VERIFICATION_TIMEOUT = 60 * 60 * 24
```

初期値は24時間程度とする。

コード内へマジックナンバーとして埋め込まないこと。

---

# 15. メール確認成功時

有効なtokenかつ未確認ユーザーの場合:

```text
EmailVerification.verified_at = timezone.now()
User.is_active = True
```

として保存する。

完了後はログイン画面へ案内する。

例:

```text
メールアドレスの確認が完了しました。
ログインしてください。
```

自動ログインは今回実装しなくてよい。

---

# 16. 確認済みURL

既に確認済みのユーザーが再度URLを開いた場合も安全に処理する。

500エラー等にしない。

例:

```text
このメールアドレスは既に確認済みです。
```

ログイン画面への導線を表示する。

---

# 17. 無効・期限切れトークン

以下の場合:

* 改ざんされたtoken
* 存在しないUser
* 期限切れ
* email変更後の古いtoken

アプリケーションエラーを発生させない。

専用画面を表示する。

例:

```text
この確認リンクは無効または期限切れです。
確認メールを再送してください。
```

確認メール再送ページへの導線を用意する。

---

# 18. 確認メール再送

以下のようなURLを追加する。

```text
/accounts/resend-verification/
```

GET:

```text
メールアドレス入力フォーム
```

POST:

```text
入力emailを正規化
↓
対象ユーザーを検索
↓
未確認ユーザーならメール再送
↓
共通完了画面
```

ユーザー列挙を防止するため、以下の場合でも表示結果を変えすぎない。

* emailが存在しない
* 既に確認済み
* 管理者停止中
* 重複email
* 未確認

原則として共通メッセージとする。

```text
確認が必要なアカウントが存在する場合、
確認メールを送信しました。
```

---

# 19. 再送による管理者停止解除を禁止

以下の状態:

```text
EmailVerification.verified_at != None
User.is_active == False
```

は「確認済みだが管理者等によって停止されている可能性がある」。

このユーザーを確認メール再送によって

```python
is_active = True
```

へ戻してはいけない。

再送対象は、

```text
今回のメール確認フローで作成された
未確認ユーザー
```

に限定する。

---

# 20. 再送連打対策

`last_sent_at` を利用し、短時間に大量送信されないようにする。

初期値の目安:

```text
60秒
```

同一ユーザーへの再送要求が短時間に繰り返された場合は、実際のメール送信を行わなくてよい。

ただし画面上のレスポンスを変え、アカウント存在有無を推測できるようにしない。

---

# 21. メール送信失敗

メール送信処理で例外が発生した場合も500エラーにしない。

新規登録時にUserとEmailVerificationが作成済みの場合は、未確認状態のまま保持する。

```text
User.is_active=False
EmailVerification.verified_at=None
```

ユーザーには、

```text
確認メールを送信できませんでした。
時間を置いて再送してください。
```

等の案内と再送ページへの導線を表示する。

例外はloggerへ記録する。

メール送信エラーの詳細、APIキー、認証情報等をブラウザへ表示しない。

---

# 22. メール送信処理の分離

メール確認機能を特定のメール配送サービスへ密結合させない。

Viewから直接Resend APIやAmazon SES APIを呼び出さない。

アプリケーション側では原則としてDjangoのメールAPIを使用する。

例:

```python
from django.core.mail import send_mail
```

または、

```python
from django.core.mail import EmailMultiAlternatives
```

必要に応じてメール生成処理を以下のようなファイルへ分離する。

```text
accounts/services.py
accounts/utils.py
accounts/tokens.py
```

ただし不要にファイルを細分化しすぎない。

---

# 23. メール配送の環境別方針

メール配送方式は環境ごとに切り替える。

## 23.1 ローカル開発環境

ローカルでは現在の

```python
django.core.mail.backends.console.EmailBackend
```

を維持する。

メールは実送信せず、開発用ターミナルへ内容を出力する。

```text
Django
↓
console.EmailBackend
↓
ターミナル
```

---

## 23.2 Render仮公開環境

現在のRender環境は本番移行前の仮公開・検証環境として扱う。

Render無料環境ではSMTPを前提としない。

RenderではHTTPSを利用したメールAPIを使用する。

今回の候補は **Resend HTTP API** とする。

構成:

```text
Render
↓
Django
↓ HTTPS
Resend API
↓
ユーザーのメールアドレス
```

SMTP接続は使用しない。

可能であればDjangoのメールAPIとの互換性を保てるBackendを利用する。

候補:

```text
django-anymail + Resend
```

ただし、アプリの認証ロジックをResend固有APIへ直接依存させない。

---

# 24. Render用設定

Render環境では環境変数によってメールBackendを切り替えられる構成とする。

APIキーをコードへ直接記述しない。

例:

```text
EMAIL_PROVIDER=resend
RESEND_API_KEY=...
DEFAULT_FROM_EMAIL=...
```

実際の変数名は既存設定規約に合わせてよい。

APIキーはRender Environment Variablesへ設定する。

Gitへコミットしない。

`.env.example` 等が存在する場合は、秘密値を含めず必要な環境変数名のみ追記する。

---

# 25. 将来のAWS本番環境

将来的に以下へ移行予定。

```text
独自ドメイン
+
AWS
```

AWS本番環境では **Amazon SES** の使用を想定する。

SMTPではなく、可能であれば **Amazon SES API** を使用する。

構成イメージ:

```text
EC2 / Django
↓
IAM Role
↓
Amazon SES API
↓
ユーザー
```

EC2等のAWSリソースからSES APIを使用する際は、将来的にIAMロールを利用する構成を優先する。

SMTPユーザー名・SMTPパスワードをアプリへ直接持たせる構成は優先しない。

---

# 26. AWS移行時に認証ロジックを変更しない

今回実装する認証機能について、

```text
RenderではResend
AWSではSES
```

という違いを、認証処理そのものへ持ち込まない。

理想形:

```text
accounts/views.py
        ↓
Django Mail API
        ↓
EMAIL_BACKEND
        ↓
環境によって配送サービス変更
```

つまり、

```text
ローカル
→ Console

Render
→ Resend API

AWS
→ Amazon SES API
```

とBackendだけを差し替えられる設計にする。

AWS移行時に以下を原則変更しなくてよい構成とする。

* SignupForm
* email verification token
* verify view
* resend view
* メールテンプレート
* 認証フロー

---

# 27. 今回の外部メールサービス実装範囲

今回のRender仮公開環境では、メール確認機能を実際に検証できるようにするため、Resend HTTP APIによるメール送信対応まで実装対象としてよい。

ただし以下は禁止。

* ViewからResend APIを直接呼び出す
* 認証ロジックをResend専用コードにする
* 将来SESへ変更できない構成にする
* SMTPを前提とした設計に固定する

AWS SESへの実際の切り替え実装は今回の必須範囲外とする。

AWS移行時の方針をドキュメントへ残す。

---

# 28. LoginView

一般ユーザー向けログインはDjango標準 `LoginView` の仕組みを可能な限り維持する。

専用AuthenticationFormを指定する形を優先する。

これにより既存の以下を維持する。

* セッションログイン
* CSRF
* `next`
* `LOGIN_REDIRECT_URL`
* Django標準LogoutView
* Django標準PasswordResetView

URL構成を大きく変更しないこと。

---

# 29. nextリダイレクト

以下の既存動作を維持する。

```text
ログイン必須画面
↓
/accounts/login/?next=/mypage/
↓
ログイン成功
↓
/mypage/
```

外部URLへリダイレクトできるopen redirectを作らない。

Django標準LoginViewの安全なnext処理を可能な限り利用する。

---

# 30. パスワード再設定

既存のDjango標準パスワード再設定機能を維持する。

パスワード再設定自体を独自実装へ置き換えない。

既存のパスワード再設定メールについても、将来的には今回のメールBackend切替によって実メール送信できる構成とする。

つまり、

```text
メール確認メール
パスワード再設定メール
```

の双方が同じDjangoメール設定を利用する。

未確認ユーザーは `is_active=False` のため、通常のパスワード再設定ではなく確認メール再送を利用する。

---

# 31. username依存表示の修正

一般ユーザー向け画面で以下のような表示が存在する場合は見直す。

```django
{{ user.username }}
{{ user.get_username }}
```

対象候補:

* `templates/base.html`
* `templates/mypage.html`
* 認証画面
* メールテンプレート
* その他username表示箇所

新規ユーザーのusernameは内部IDになるため、通常画面へ表示しない。

必要な場合はemailを表示する。

ただしemailが空の既存ユーザーについてもテンプレートエラーにならないようにする。

---

# 32. パスワード再設定メール

`password_reset_email.html` にusernameを含めている場合は削除する。

以下のような文面でよい。

```text
パスワード再設定のリクエストを受け付けました。

以下のURLから新しいパスワードを設定してください。
```

内部生成usernameをメール本文へ表示しないこと。

---

# 33. パスワード表示 / 非表示

パスワードフィールドに表示切替ボタンを追加する。

対象:

* ログイン
* 新規登録 password1
* 新規登録 password2
* パスワード再設定
* 新パスワード設定
* その他 `fields.html` を利用するpasswordフィールド

共通 `templates/registration/fields.html` を利用して実装できる場合は共通化する。

---

# 34. パスワード表示切替HTML

password inputの横にbuttonを配置する。

buttonは必ず

```html
type="button"
```

とする。

フォームsubmitにならないこと。

アクセシビリティを考慮し、

```html
aria-label
aria-pressed
```

等を適切に設定する。

入力欄の

```text
name
id
value
autocomplete
```

等を壊さない。

---

# 35. パスワード表示切替JavaScript

認証画面用JavaScriptを追加してよい。

例:

```text
static/js/auth.js
```

クリック時:

```text
password
↓
text
↓
password
```

と切り替える。

JavaScriptが無効でも通常のpassword入力として利用できること。

外部JSライブラリは追加しない。

Vanilla JavaScriptで実装する。

---

# 36. SCSS

認証画面のスタイルは既存 `auth.scss` を基準に追加する。

対象:

```text
static/scss/auth.scss
```

実装後:

```bash
npm run sass
```

を実行してコンパイル済みCSSも更新する。

対象:

```text
static/styles/auth.css
```

SCSSだけ変更してCSSを更新し忘れないこと。

---

# 37. 追加・変更対象ファイル候補

実際の既存構成を確認したうえで決定する。

```text
accounts/
├── models.py
├── forms.py
├── views.py
├── tests.py
├── services.py        # 必要なら追加
└── utils.py           # 必要なら追加

config/
├── settings.py
└── urls.py

templates/
├── base.html
├── mypage.html
└── registration/
    ├── base.html
    ├── fields.html
    ├── login.html
    ├── signup.html
    ├── password_reset_email.html
    ├── verification_sent.html
    ├── verification_invalid.html
    ├── verification_complete.html
    ├── resend_verification.html
    └── verification_email.txt

static/
├── js/
│   └── auth.js
├── scss/
│   └── auth.scss
└── styles/
    └── auth.css

docs/
├── project-spec.md
└── deploy/
    └── render.md
```

依存パッケージを追加する場合は、

```text
requirements.txt
```

等も更新する。

ファイル名は既存プロジェクト規約に合わせて調整してよい。

---

# 38. マイグレーション

今回DB変更が必要なのは、原則としてメール確認状態管理用モデルのみ。

例:

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

標準 `auth_user` のemailカラムへunique制約を追加しない。

既存Userデータを自動削除・統合・正規化するmigrationを作成しない。

---

# 39. テスト

既存テストを削除して帳尻を合わせないこと。

今回の実装に合わせてテストを追加・修正する。

最低限以下をテストする。

## 新規登録

* username入力欄が存在しない
* emailが必須
* email前後空白が正規化される
* emailの大文字小文字が正規化される
* 内部usernameが自動生成される
* passwordが正しく設定される
* 登録直後 `is_active=False`
* EmailVerificationが作成される
* 確認メール送信処理が呼ばれる
* 確認URLがメール本文に含まれる

## 重複メール

以下を同一として拒否する。

```text
test@example.com
TEST@example.com
 Test@example.com
```

## メール確認

* 正しいtokenで確認成功
* `verified_at` がセットされる
* `is_active=True` になる
* 確認後ログイン可能
* 無効tokenを安全に処理
* 改ざんtokenを安全に処理
* 期限切れtokenを安全に処理
* 確認済みURL再アクセスを安全に処理

## 未確認ログイン

```python
is_active=False
```

の未確認ユーザーが通常ログインできないこと。

## メールログイン

* 正しいemail + passwordで成功
* email大文字小文字違いでも成功
* email前後空白があっても成功
* password不正で失敗
* 存在しないemailで失敗
* `is_active=False` で失敗

## 既存ユーザー

EmailVerificationを持たない既存activeユーザーが、emailが一意ならメールログインできること。

## 既存重複メール

同一emailを持つUserが複数存在する場合、どちらかを勝手にログインさせないこと。

## Admin

既存管理者が

```text
/admin/
username + password
```

でログイン可能なこと。

## 確認メール再送

* 未確認ユーザーへ再送できる
* 存在しないemailでも安全な共通レスポンス
* 確認済みemailでも安全な共通レスポンス
* 管理者停止ユーザーを再有効化しない
* 短時間再送を抑制できる

## メール送信失敗

メール送信処理をmockし、

* 500エラーにならない
* Userが未確認状態で残る
* 再送導線が表示される

ことを確認する。

## next

```text
/accounts/login/?next=/mypage/
```

でログイン後 `/mypage/` へ戻ること。

外部URL:

```text
/accounts/login/?next=https://evil.example/
```

へリダイレクトしないこと。

## パスワード表示切替

HTMLテストとして最低限、

* password inputが存在する
* toggle buttonが存在する
* `type="button"`
* 対象inputを識別できる属性がある

ことを確認する。

JavaScriptのブラウザE2Eテストまでは今回必須としない。

---

# 40. CSRF・セキュリティ

既存のDjangoセキュリティ機能を維持する。

特に以下を守ること。

* CSRF対策
* Django標準password hash
* Django標準session
* open redirect防止
* ユーザー列挙防止
* token改ざん防止
* token期限
* メール送信エラーの内部情報非表示
* メールAPIキーの秘匿

パスワードを独自暗号化・独自hashしない。

パスワードをログ出力しない。

確認tokenをログへ不用意に記録しない。

Resend APIキー、将来のAWS認証情報等をGitへコミットしない。

---

# 41. project-spec.md更新

実装完了後 `docs/project-spec.md` の認証仕様を更新する。

最低限以下を反映する。

```text
新規登録
- email
- password
- password confirmation
- username入力なし
- 登録直後is_active=False
- 確認メール送信

メール確認
- 確認URL
- 有効期限
- 確認完了後is_active=True
- 再送機能

ログイン
- email + password

管理画面
- username + passwordを維持

パスワード再設定
- Django標準機能を維持

メール配送
- ローカル: console.EmailBackend
- Render: Resend HTTP API
- 将来AWS: Amazon SES APIを想定
```

URL一覧にも追加URLを反映する。

---

# 42. README更新

READMEに認証方法や開発環境のメール確認方法が記載されている場合は更新する。

最低限、開発者がローカルで確認メール内容を確認する方法が分かる状態にする。

不要な場合は無理に変更しなくてよい。

---

# 43. Renderドキュメント

`docs/deploy/render.md` を更新する。

今回のメール構成を記載する。

```text
ローカル開発
→ console.EmailBackend

Render仮公開
→ Resend HTTP API
→ SMTPは使用しない

将来AWS本番
→ Amazon SES APIへ切り替え予定
```

Render上で必要になる環境変数も記載する。

例:

```text
RESEND_API_KEY
DEFAULT_FROM_EMAIL
SITE_URL
```

実際の名称は実装と統一する。

秘密値そのものはドキュメントへ書かない。

---

# 44. RenderとAWSのURL差分

確認メールに含めるURLは環境ごとに切り替え可能にする。

例:

```text
ローカル:
http://localhost:8000

Render:
https://xxxx.onrender.com

AWS本番:
https://独自ドメイン
```

可能であればリクエスト情報やDjango Sites相当の仕組みを利用する。

固定URLを各Viewへ直接記述しない。

環境変数を使う場合は、

```text
SITE_URL
```

等にまとめる。

---

# 45. 将来のAWS移行について

今回AWSインフラ自体は変更しない。

以下は将来対応とする。

```text
独自ドメイン取得
Route 53設定
Amazon SESでドメイン認証
DKIM等のDNS設定
SES Sandbox解除
IAM Role設定
SES API用Email Backend設定
```

ただし今回のDjango認証実装は、これらの変更時に大規模改修が不要な構成にしておく。

---

# 46. 実装順序

以下の順序で進める。

1. AGENTS / project-spec /既存コード確認
2. 既存テスト実行
3. email正規化処理
4. SignupForm変更
5. EmailVerificationモデル追加
6. migration作成
7. 確認token生成処理
8. 確認メール生成処理
9. 確認URL / View実装
10. 再送機能実装
11. EmailAuthenticationForm実装
12. LoginViewへ適用
13. username依存UI修正
14. パスワード表示切替実装
15. SCSS修正
16. `npm run sass`
17. Render用Resend HTTP API対応
18. 環境別EMAIL_BACKEND設定
19. テスト追加
20. 全テスト実行
21. `project-spec.md` 更新
22. `docs/deploy/render.md` 更新
23. 必要ならREADME更新

---

# 47. 実装後の確認コマンド

Docker環境に合わせて適切なコマンドを使用する。

例:

```bash
docker compose exec web python manage.py makemigrations --check
docker compose exec web python manage.py check
docker compose exec web python manage.py test
```

SCSS変更後:

```bash
npm run sass
```

依存パッケージを追加した場合はDocker buildも確認する。

```bash
docker compose up -d --build
```

既存プロジェクトの実行方法が異なる場合はそちらを優先する。

---

# 48. やってはいけないこと

以下は禁止。

* カスタムUserへの移行
* `AUTH_USER_MODEL` の変更
* 既存Userテーブルの破壊的変更
* 既存ユーザーの自動削除
* 重複ユーザーの勝手な統合
* email unique制約の無断追加
* Adminログイン方式の破壊
* django-allauthの無断導入
* アプリの認証ロジックをResend専用にする
* Viewから直接外部メールAPIを呼ぶ
* RenderでSMTP利用を前提にする
* 将来SESへ変更できない構成にする
* パスワード認証の独自hash実装
* CSRF無効化
* SSL検証無効化
* `next` を無検証でredirect
* APIキーをGitへコミット
* 既存テストを削除してテスト成功扱いにする
* unrelatedなリファクタリング
* UI全体の無断リデザイン

今回の認証改修に必要な範囲へ変更を限定すること。

---

# 49. 完了条件

以下をすべて満たした場合に完了とする。

* [ ] 新規登録画面からusername入力がなくなっている
* [ ] email + passwordで新規登録できる
* [ ] 内部usernameが自動生成される
* [ ] 新規ユーザーは登録直後 `is_active=False`
* [ ] EmailVerificationが作成される
* [ ] 確認メールが生成される
* [ ] 有効な確認URLでアカウントが有効化される
* [ ] 無効・期限切れURLを安全に処理できる
* [ ] 確認メールを再送できる
* [ ] ユーザー列挙を防止している
* [ ] 管理者停止ユーザーを再送で復活させない
* [ ] email + passwordでログインできる
* [ ] 未確認ユーザーはログインできない
* [ ] 既存activeユーザーは条件を満たせばメールログインできる
* [ ] 重複emailユーザーを誤認証しない
* [ ] `/admin/` のusernameログインが維持されている
* [ ] password resetが引き続き利用できる
* [ ] `next` リダイレクトが維持されている
* [ ] open redirectが発生しない
* [ ] password表示 / 非表示切替が動作する
* [ ] SCSSとCSSが同期している
* [ ] ローカルではconsole.EmailBackendが利用できる
* [ ] RenderではResend HTTP APIで実メール送信できる
* [ ] SMTPへ依存していない
* [ ] メール配送処理が認証ロジックから分離されている
* [ ] 将来Amazon SES APIへ切替可能な構成になっている
* [ ] APIキーがコードへハードコードされていない
* [ ] Django checkが通る
* [ ] 既存テストが通る
* [ ] 新規テストが通る
* [ ] `docs/project-spec.md` が更新されている
* [ ] `docs/deploy/render.md` が更新されている

---

# 50. 作業完了時の報告

作業完了後、チャットには長い説明を出さず、以下だけ簡潔に報告すること。

```text
実装内容
- メールログイン対応
- メール確認フロー追加
- 確認メール再送追加
- パスワード表示切替追加
- Render向けResend API対応

主な変更ファイル
- ...

Migration
- ...

メール配送
- Local: console
- Render: Resend API
- AWS: SES APIへ将来切替予定

テスト
- xx件成功

Renderで必要な環境変数
- ...

未対応
- Amazon SESへの実接続
- AWS本番環境への移行
```

本番AWS移行やAmazon SES設定を今回実施していない場合は、必ず未対応事項として明示すること。
