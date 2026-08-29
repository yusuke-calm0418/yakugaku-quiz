# yakugaku-quiz 仕様書 & プロジェクトガイド

薬剤師国家試験対策向けの Django 製クイズWebアプリケーションの仕様書および開発ガイドラインです。

---

## 1. プロジェクト概要

- **名称**: yakugaku-quiz（薬剤師国家試験対策クイズ）
- **目的**: 薬剤師国家試験の過去問・演習問題をスキマ時間で手軽に学習できるクイズ形式のWebサービス。
- **ターゲット**: 薬学部生・薬剤師国家試験受験生

---

## 2. 技術スタック・インフラ構成

| 区分 | 技術 | バージョン/備考 |
|---|---|---|
| 言語 | Python | 3.12 |
| フレームワーク | Django | 5.x / 6.x系 |
| データベース | PostgreSQL | 15 (Dockerコンテナ) |
| コンテナ環境 | Docker / Docker Compose | |
| フロントエンド | HTML5, Vanilla JavaScript, CSS | |
| 認証 | Django標準認証 (`django.contrib.auth`) | セッション認証 |

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
| `text` | TextField | NOT NULL | 問題文 |
| `choice1` | CharField(255) | NOT NULL | 選択肢1 |
| `choice2` | CharField(255) | NOT NULL | 選択肢2 |
| `choice3` | CharField(255) | NOT NULL | 選択肢3 |
| `choice4` | CharField(255) | NOT NULL | 選択肢4 |
| `correct` | CharField(10) | NOT NULL | 正解番号（文字列）。単一正解なら `'1'`、複数正解なら `'13'` のように連結して保持 |
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
- **新規登録 (`/accounts/signup/`)**: `UserCreationForm` を使用したユーザー作成。登録後はログイン画面へリダイレクト。
- **ログイン (`/accounts/login/`)**: Django標準のログイン画面。
- **ログアウト (`/accounts/logout/`)**: POSTリクエストによるセーフログアウト。

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
   - **必須問題 (`required`)**: ラジオボタン（単一選択）
   - **一般問題 (`general`)**: チェックボックス（複数選択）。JavaScriptにより **最大2つまで** しか選択できないよう制限。

3. **採点・履歴保存 (POST)**:
   - 選択された選択肢（リスト）と問題の正解文字列を順不同で照合比較 (`sorted(selected) == sorted(correct_answers)`)。
   - 正誤判定結果 (`is_correct`) と回答内容を `Answer` レコードとして保存。
   - 正解 / 不正解、選択肢に応じた正解テキスト、解説文を表示。
   - 「次の問題へ」ボタンで同一条件の次の問題を取得。

4. **学習進捗表示**:
   - ユーザーの通算正答率（正解数 / 総回答数）を画面上にリアルタイム表示。

### 5.4 マイページ (`/mypage/`)
ユーザーの学習成果・統計情報を確認できます。
- 累計回答数 (`total`)
- 累計正解数 (`correct`)
- 全体正答率 (`accuracy` %)
- 苦手問題数 (`weak_count` : 正答率50%未満の問題数)

### 5.5 管理画面 (`/admin/`)
- 問題（`Question`）の追加・編集・削除
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
