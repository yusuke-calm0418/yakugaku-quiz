# 問題画像表示機能仕様

## 1. 概要

薬剤師国家試験の過去問には、構造式・グラフ・模式図・化学構造など、
画像がないと問題として成立しにくい設問が存在する。

そのため、`quiz.Question` に任意の問題画像を1枚登録できる機能を追加し、
問題画面およびDjango Adminから扱えるようにする。

初期実装では複雑な画像管理は行わず、**1問につき問題画像1枚**を基本とする。

---

## 2. 対象

対象モデル：

```text
quiz.models.Question
```

対象画面：

- Django Admin の Question 追加・編集画面
- クイズ問題表示画面

CSVインポート機能自体から画像ファイルをアップロードする機能は、
今回の必須要件には含めない。

---

## 3. 基本方針

画像を使用しない問題は、現在の表示・登録方法をそのまま維持する。

画像を使用する問題のみ、Questionに登録された画像を表示する。

表示順は以下とする。

```text
問題文
↓
問題画像（画像が登録されている場合のみ）
↓
選択肢
```

---

## 4. Questionモデル

Questionモデルに任意の画像フィールドを追加する。

フィールド名は以下を使用する。

```text
question_image
```

想定実装：

```python
question_image = models.ImageField(
    upload_to="questions/",
    blank=True,
    null=True,
)
```

既存Questionとの互換性を維持するため、画像は必須にしない。

必要なmigrationを作成する。

---

## 5. 画像ファイル

初期実装では以下の画像形式を想定する。

```text
PNG
JPEG / JPG
WebP
```

画像アップロードに `Pillow` が必要な場合は、
既存の依存関係を確認したうえで `requirements.txt` に追加する。

SVG対応は今回の必須要件には含めない。

---

## 6. 画像サイズ

管理画面から極端に大きなファイルを登録しないようにする。

目安として、1ファイルあたり最大5MB程度までを許容する。

既存のバリデーション構成を確認し、
必要であればQuestionモデルまたはフォーム側に画像サイズチェックを追加する。

過度な画像加工・自動リサイズ機能は今回実装しなくてよい。

---

## 7. Django Admin

Questionの追加・編集画面から `question_image` を登録・変更・削除できるようにする。

既存のQuestionAdminに存在する以下の機能は維持する。

- 検索
- フィルター
- CSVインポート
- その他既存の管理機能

既存QuestionAdminを全面的に置き換えず、現在の設定に統合すること。

可能であればAdmin上で現在の画像を確認できるようにする。

ただし画像プレビューは必須要件ではない。

---

## 8. クイズ画面

Questionに `question_image` が登録されている場合のみ、
問題文の下・選択肢の上に画像を表示する。

Django templateの想定：

```django
{% if question.question_image %}
  <img
    src="{{ question.question_image.url }}"
    alt="問題図"
    class="question-image"
  >
{% endif %}
```

実際のテンプレート構造は既存コードを確認して統合すること。

---

## 9. レスポンシブ表示

問題画像はPC・タブレット・スマートフォンで表示崩れを起こさないこと。

最低限以下を満たす。

```css
.question-image {
  display: block;
  max-width: 100%;
  height: auto;
}
```

PC表示では必要以上に拡大しないよう、
既存デザインに合わせて適切な最大幅を設定してよい。

画像の縦横比を維持する。

横スクロールが発生しないようにする。

---

## 10. 選択肢自体が画像の場合

構造式など、選択肢そのものが画像になっている問題については、
初期実装では選択肢ごとに個別画像フィールドを持たせない。

代わりに、

**設問中の図 + 選択肢1〜6の図を1枚の画像としてまとめて登録する。**

例：

```text
問題文

┌─────────────────────┐
│       A の構造式      │
│                     │
│  1  2  3  4  5      │
│ 各選択肢の構造式      │
└─────────────────────┘

○ 1
○ 2
○ 3
○ 4
○ 5
```

回答操作には既存のラジオボタンまたはチェックボックスを使用する。

この場合、CSVの `choice1` ～ `choice6` には、
以下のような番号表示用の値を登録してよい。

```text
1
2
3
4
5
6
```

または、既存データ形式に合わせて管理する。

---

## 11. CSVインポートとの関係

現在のCSVインポート機能は問題テキスト・選択肢・正答・解説等の登録に使用する。

今回の初期実装では、CSVから画像ファイル自体をアップロードしない。

運用フロー：

```text
CSVで問題を一括登録
↓
画像が必要なQuestionだけDjango Adminで開く
↓
question_imageをアップロード
↓
保存
```

`question_code` が実装済みの場合は、
画像を登録するQuestionの識別にも `question_code` を利用する。

---

## 12. MEDIA設定

開発環境でDjangoのアップロード画像を表示できるよう、
既存設定を確認する。

必要に応じて以下を設定する。

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

開発環境では、必要に応じてプロジェクトURL設定に
media配信用の設定を追加する。

例：

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    ...
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
```

既に同等の設定が存在する場合は重複追加しない。

---

## 13. Git管理

Adminからアップロードした画像はアプリケーションコードとは分離して管理する。

開発用の `media/` ディレクトリを使用する場合、
原則としてGit管理対象外とする。

必要に応じて `.gitignore` を確認し、

```text
media/
```

を追加する。

既に適切な設定がある場合は変更不要。

---

## 14. 本番環境

初期実装ではローカルMEDIAによる動作確認を行う。

ただし、将来的にAWS本番環境ではS3等のオブジェクトストレージへ
移行できる構成を前提とする。

そのため、

- テンプレートに画像URLをハードコードしない
- ファイルシステムの絶対パスをコードに埋め込まない
- `question.question_image.url` を利用する

こと。

S3対応そのものは今回の必須要件には含めない。

---

## 15. 既存5択・6択対応との共存

Questionが `choice1` ～ `choice6` に対応している場合、
画像機能追加後も既存の5択・6択表示および採点処理が正常に動作すること。

画像の有無によって回答ロジックを分岐させない。

画像は問題表示を補助するデータとして扱う。

---

## 16. セキュリティ

画像アップロードはDjango Adminからのみ行う。

一般ユーザーが任意ファイルをアップロードできる機能は作成しない。

アップロードされた画像をHTMLとして解釈しない。

既存のAdmin権限制御を維持する。

---

## 17. 主な変更対象候補

実装前に既存構成を確認する。

主に以下が変更候補となる。

```text
requirements.txt
quiz/models.py
quiz/admin.py
config/settings.py
config/urls.py
templates/quiz/question.html
SCSS / CSS関連ファイル
.gitignore
```

必要なファイルだけ変更すること。

既に同等機能が存在する場合は重複実装しない。

---

## 18. テスト要件

最低限以下を確認する。

### モデル

- question_imageなしのQuestionを保存できる
- question_imageありのQuestionを保存できる
- 既存Questionに影響がない

### Admin

- Question追加画面から画像を登録できる
- Question編集画面から画像を変更できる
- 画像を削除して保存できる
- 既存CSVインポート機能が壊れていない

### 問題画面

- 画像なし問題が従来通り表示される
- 画像あり問題では問題文の下に画像が表示される
- 画像の下に選択肢が表示される
- 5択問題と併用できる
- 6択問題と併用できる
- 正誤判定に影響しない

### レスポンシブ

- PCで画像がレイアウトからはみ出さない
- スマートフォンで画像が画面幅を超えない
- 画像の縦横比が維持される

---

## 19. 今回実装しないもの

以下は将来拡張とし、今回の実装対象外とする。

- CSVファイルと画像ZIPの同時アップロード
- CSVから画像ファイルを直接登録する処理
- 1つのQuestionへの複数画像登録
- 選択肢ごとの個別画像フィールド
- 画像への拡大・ズームUI
- 画像の自動トリミング
- 画像の自動圧縮
- S3への保存切替
- CloudFrontによる画像配信

必要になった段階で別機能として仕様化する。

---

## 20. 完了条件

以下をすべて満たした場合に完了とする。

- Questionに任意の問題画像を登録できる
- 必要なmigrationが作成されている
- Django Adminから画像をアップロードできる
- 画像なし問題が従来通り動作する
- 画像あり問題で画像が正しい位置に表示される
- 画像がレスポンシブ表示される
- 5択・6択問題と共存できる
- 既存CSVインポートが壊れていない
- 開発環境でmedia画像を表示できる
- 関連テストが成功する
- 関連ドキュメントが実装内容と一致している

---

## 21. 実装時の確認事項

実装開始前に最低限以下を確認する。

```text
AGENTS.md
docs/project-spec.md
docs/product-specs/question-csv-import.md
docs/product-specs/question-image-support.md
docs/agent/development.md
docs/agent/design.md
quiz/models.py
quiz/admin.py
quiz/views.py
templates/quiz/question.html
config/settings.py
config/urls.py
```

実際のファイル名・配置が異なる場合は既存プロジェクト構成を優先する。

既存実装と本仕様に差異がある場合は、
既存コードと `docs/project-spec.md` の整合性を確認してから修正する。

大規模な設計変更を独断で行わない。
