# 問題CSVインポート機能仕様

## 1. 概要
Django管理画面からCSVファイルをアップロードし、`quiz.Question` の問題データを一括登録・更新できる機能を実装する。
問題数が増えた場合でも、Django Adminから1件ずつ登録する必要がない運用を目的とする。
実装には原則として `django-import-export` を利用する。

---

## 2. 対象
対象モデル：

```text
quiz.models.Question
```

Django Admin上のQuestion管理画面からCSVインポートを実行できるようにする。
回答履歴である `Answer` はインポート対象外とする。

---

## 3. 使用ライブラリ
以下を利用する。
```text
django-import-export
```
必要に応じて `requirements.txt` に追加する。
Django Adminの既存機能を維持したまま、Question管理画面にCSVインポート機能を追加する。
CSVエクスポート機能は今回の必須要件ではない。
---

## 4. Questionモデルの変更
CSV上の問題を一意に識別するため、Questionモデルに以下のフィールドを追加する。
```text
question_code
```

仕様：

| 項目     | 内容              |
| ------ | --------------- |
| フィールド名 | `question_code` |
| 型      | `CharField`     |
| 最大文字数  | 50              |
| 用途     | CSVインポート時の問題識別子 |
| 重複     | 不可              |
| 既存データ  | 未設定を許容          |

既存データとの互換性を維持するため、既存QuestionについてはNULLまたは空値を許容する。

CSV経由で登録するQuestionでは `question_code` を必須とする。

実装時はマイグレーションを作成すること。

例：

```text
109-PHA-001
109-PHA-002
110-REQ-001
```

`question_code` はDjangoの内部IDである `id` とは別に管理する。

CSVの再インポート時には `question_code` をキーとして既存Questionを特定する。

---

## 5. CSVフォーマット

CSVの1行をQuestionの1レコードとして扱う。

### CSVカラム

```csv
question_code,text,choice1,choice2,choice3,choice4,choice5,choice6,correct,explanation,category,question_type
```

カラムの意味：

| CSVカラム          | Questionフィールド   | 内容     |
| --------------- | --------------- | ------ |
| `question_code` | `question_code` | 問題管理番号 |
| `text`          | `text`          | 問題文    |
| `choice1`       | `choice1`       | 選択肢1   |
| `choice2`       | `choice2`       | 選択肢2   |
| `choice3`       | `choice3`       | 選択肢3   |
| `choice4`       | `choice4`       | 選択肢4   |
| `choice5`       | `choice5`       | 選択肢5（空欄可） |
| `choice6`       | `choice6`       | 選択肢6（空欄可） |
| `correct`       | `correct`       | 正解番号   |
| `explanation`   | `explanation`   | 解答・解説  |
| `category`      | `category`      | 出題分野   |
| `question_type` | `question_type` | 問題種別   |

CSVヘッダー名は上記を使用する。`choice5`・`choice6`以外は必須カラム。

`choice5`・`choice6`はCharField(255)、空欄可、既定値は空文字。既存問題は空文字として移行する。
旧4択CSVとの互換性のため、この2列は省略も可能。列を省略した場合、新規登録では空文字、更新では既存値を保持する。列があり値が空欄の場合は既存値も空文字へ更新する。

カラム順については固定せず、ヘッダー名を基準として読み込む。

---

## 6. CSV例

```csv
question_code,text,choice1,choice2,choice3,choice4,choice5,choice6,correct,explanation,category,question_type
109-PHA-001,アセトアミノフェンについて正しいものはどれか。,選択肢1,選択肢2,選択肢3,選択肢4,選択肢5,,5,アセトアミノフェンについての解説。,pharmacology,required
109-PHA-002,ワルファリンについて正しいものを選べ。,選択肢1,選択肢2,選択肢3,選択肢4,選択肢5,選択肢6,56,ワルファリンについての解説。,pharmacology,general
```

問題文や解説内にカンマ・改行を含む場合は、標準的なCSV形式に従いダブルクォートで囲む。

例：

```csv
109-PHA-003,"次の記述について、正しいものを選べ。","選択肢1","選択肢2","選択肢3","選択肢4",,,"24","1つ目の解説。
2つ目の解説。",pharmacology,general
```

---

## 7. 文字コード

CSVは以下の文字コードをサポート対象とする。

```text
UTF-8
UTF-8 with BOM
```

日本語を含むことを前提とする。

Shift_JIS / CP932への対応は初期実装の必須要件にはしない。

---

## 8. category

以下の値のみ許可する。

```text
physics_chemistry_biology
hygiene
pharmacology
pharmaceutics
pathology
law_ethics
practice
```

表示名：

| 値                           | 表示       |
| --------------------------- | -------- |
| `physics_chemistry_biology` | 物理・化学・生物 |
| `hygiene`                   | 衛生       |
| `pharmacology`              | 薬理       |
| `pharmaceutics`             | 薬剤       |
| `pathology`                 | 病態・薬物治療  |
| `law_ethics`                | 法規・制度・倫理 |
| `practice`                  | 実務       |

上記以外の値が入力された場合はインポートエラーとする。

---

## 9. question_type

以下の値のみ許可する。

```text
required
general
```

### required

必須問題。

正解は1つのみ。

例：

```text
1
2
3
4
5
6
```

### general

一般問題。

正解は1つまたは2つ。

例：

```text
1
13
24
34
```

---

## 10. correctのバリデーション

`correct` は文字列として扱う。

使用できる文字：

```text
1
2
3
4
5
6
```

のみ。

以下はエラーとする。

```text
0
7
12a
11
123
```

同じ選択肢番号を重複して指定してはいけない。空欄の選択肢を正解に指定した場合もエラーとする。
この正解検証はCSVインポートと管理画面の追加・編集で共通とする。

### requiredの場合

正解は必ず1つ。

OK：

```text
1
```

NG：

```text
12
```

### generalの場合

正解は1つまたは2つ。

OK：

```text
2
13
24
```

3つ以上の正解はエラーとする。

---

## 11. 必須項目

CSVインポート時、以下は空欄不可とする。

```text
question_code
text
choice1
choice2
choice3
choice4
correct
explanation
category
question_type
```

値の前後に不要な空白が存在する場合は、可能な範囲で除去してから処理する。

---

## 12. 新規登録・更新ルール

CSVインポートでは `question_code` をレコード識別キーとする。

### question_codeがDBに存在しない場合

新規Questionとして登録する。

例：

```text
CSV: 109-PHA-001
DB: 存在しない

→ 新規登録
```

### question_codeがDBに存在する場合

既存QuestionをCSVの内容で更新する。

例：

```text
CSV: 109-PHA-001
DB: 109-PHA-001が存在

→ 既存Questionを更新
```

これにより、同一CSVを再インポートしても同じ問題が重複登録されないようにする。

---

## 13. CSV内の重複

同じCSV内に同一 `question_code` が複数存在する場合はエラーとする。

例：

```text
109-PHA-001
109-PHA-002
109-PHA-001
```

この場合はインポートを実行しない。

---

## 14. インポートフロー

Django Adminから以下の流れで操作できること。

```text
Django Admin
    ↓
Question一覧
    ↓
CSVインポート
    ↓
CSVファイル選択
    ↓
アップロード
    ↓
インポート内容・エラー確認
    ↓
確認
    ↓
DB登録
```

可能な限り `django-import-export` 標準のプレビュー・確認画面を利用する。

管理者が内容を確認せず即座にDBへ登録される仕様にはしない。

---

## 15. エラー時の挙動

CSVの一部に不正なデータが存在する場合、エラー内容を管理画面上で確認できるようにする。

例：

```text
3行目: category に不正な値が指定されています。
5行目: required の correct に複数の正解が指定されています。
8行目: question_code が重複しています。
```

可能な限り行番号と原因を確認できるようにする。

### DB登録

バリデーションエラーが存在する場合は、不完全な状態で一部だけ登録しないこと。

原則として、

```text
全件成功
または
全件失敗
```

となるようトランザクションを利用する。

---

## 16. Django Admin

既存のQuestion管理画面の、

* 一覧
* 新規追加
* 編集
* 削除

はそのまま利用可能とする。

そのうえでCSVインポート機能を追加する。

既存の `QuestionAdmin` に検索・フィルター等が存在する場合は、それらを削除しない。

既存実装を確認したうえで統合すること。

---

## 17. セキュリティ

CSVインポート機能はDjango Admin内にのみ実装する。

一般ユーザーからアクセス可能なURLとして公開しない。

Django Adminへのアクセス権限を持つユーザーのみ使用可能とする。

CSV内の値をHTMLとして実行・解釈しない。

---

## 18. 実装対象候補

既存構成を確認したうえで、主に以下のファイルが変更対象となる。

```text
requirements.txt
config/settings.py
quiz/models.py
quiz/admin.py
```

必要に応じて以下を追加する。

```text
quiz/resources.py
quiz/tests/
```

例：

```text
quiz/
├── admin.py
├── models.py
├── resources.py
└── tests/
    └── test_question_import.py
```

実際の配置については既存コード構成を優先する。

---

## 19. テスト要件

最低限、以下をテストする。

### 正常系

* 正しいCSVをインポートできる
* 1件の問題を新規登録できる
* 複数件を一括登録できる
* UTF-8の日本語CSVを登録できる
* UTF-8 BOM付きCSVを処理できる
* 同じ `question_code` を再インポートすると更新になる
* `required` の単一正解を登録できる
* `general` の複数正解を登録できる
* 5択・6択および正解5・6を登録・表示・採点できる
* choice5・choice6の空欄、省略した旧CSVの登録・更新に対応する

### 異常系

* 必須項目が空
* 不正なcategory
* 不正なquestion_type
* correctが1〜6以外
* requiredでcorrectが複数
* generalでcorrectが3つ以上
* correct内で同じ番号が重複
* CSV内でquestion_codeが重複
* 必須カラムが存在しない

### トランザクション

複数行のうち1行にエラーがある場合、正常行だけがDBへ登録されないことを確認する。

---

## 20. CSVサンプル

実装時にCSVサンプルもリポジトリへ追加する。

配置例：

```text
docs/features/samples/questions-import-sample.csv
```

サンプルには最低2件含める。

* `required` 1件
* `general` 1件

---

## 21. 完了条件

以下をすべて満たした場合に実装完了とする。

* Django AdminのQuestion画面からCSVをアップロードできる
* インポート前に内容を確認できる
* CSVからQuestionを複数登録できる
* `question_code` により既存問題を更新できる
* 同じCSVを再投入しても問題が重複しない
* categoryのバリデーションが行われる
* question_typeのバリデーションが行われる
* correctのバリデーションが行われる
* エラー時に一部だけDB登録されない
* 既存のQuestion管理機能が壊れていない
* 自動テストが追加されている
* テストが成功する
* サンプルCSVが追加されている
* `docs/project-spec.md` と実装内容に矛盾がない

---

## 22. 実装時の注意事項

実装開始前に必ず以下を確認する。

```text
AGENTS.md
docs/project-spec.md
docs/agent/development.md
docs/features/question-csv-import.md
quiz/models.py
quiz/admin.py
```

既存実装を確認せず、QuestionモデルやQuestionAdminを全面的に置き換えないこと。

既存機能との互換性を維持すること。

仕様と既存実装に矛盾がある場合は、独断で大幅変更せず差異を整理すること。

実装完了後は関連テストを実行し、結果を確認すること。
