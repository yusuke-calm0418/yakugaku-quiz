---
trigger: always_on
---

# Design Rules

このファイルは、yakugaku-quiz プロジェクトのUI・デザインに関する共通ルールを定義します。
HTML / SCSS を作成・修正する際は、原則として以下のルールに従ってください。

---

## SCSS Variables

デザインで使用する基本値は、原則としてSCSS変数で管理してください。

```scss
// Colors
$color-main: #39A378;
$color-bg: #F1F3F9;
$color-text: #19273B;
$color-red: #DC716C;
$color-yellow: #F4AA6D;
$color-line: #CDD9EA;
$color-bg-sub: #E7F4F0;

// Typography
$font-family-base: "Noto Sans JP", sans-serif;

$font-size-body: 16px;

$font-size-heading-2: 32px;
$font-size-heading-2-tablet: 28px;
$font-size-heading-2-mobile: 24px;

$line-height-base: 1.8;

// Layout
$container-width: 1200px;
$container-width-narrow: 1000px;

// Side Padding
$side-padding: 24px;
$side-padding-mobile: 16px;

// Section Spacing
$section-space-lg: 100px;
$section-space-sm: 50px;

$section-space-lg-tablet: 80px;
$section-space-sm-tablet: 40px;

$section-space-lg-mobile: 60px;
$section-space-sm-mobile: 32px;

// Breakpoints
$breakpoint-tablet: 1023px;
$breakpoint-mobile: 767px;
```

---

## Colors

原則として以下のカラーを使用してください。

| Name | SCSS Variable | Usage |
| --- | --- | --- |
| Main | `$color-main` | ボタン、強調、アクセント |
| BG | `$color-bg` | 基本背景 |
| Text | `$color-text` | 見出し・本文 |
| Red | `$color-red` | エラー、不正解、注意 |
| Yellow | `$color-yellow` | 注意、強調 |
| Line | `$color-line` | ボーダー、区切り線 |
| BG2 | `$color-bg-sub` | 淡いアクセント背景 |

- 独自の色を追加せず、原則として上記のカラーを使用する。
- 基本テキストには `$color-text` を使用する。
- `#000000` は原則使用しない。
- カラーコードを各SCSSファイルへ直接ベタ書きせず、SCSS変数を使用する。

---

## Typography

基本フォントは Google Fonts の `Noto Sans JP` を使用してください。

### Body Text

- Font Size: `16px`
- Line Height: `1.8`

### Heading 2

- PC: `32px`
- Tablet: `28px`
- Mobile: `24px`
- Line Height: `1.8`

```scss
body {
  font-family: $font-family-base;
  font-size: $font-size-body;
  line-height: $line-height-base;
  color: $color-text;
}

h2 {
  font-size: $font-size-heading-2;
  line-height: $line-height-base;
}

@media (max-width: $breakpoint-tablet) {
  h2 {
    font-size: $font-size-heading-2-tablet;
  }
}

@media (max-width: $breakpoint-mobile) {
  h2 {
    font-size: $font-size-heading-2-mobile;
  }
}
```

---

## Layout

### Container

- 基本コンテンツ最大幅: `1200px`
- 狭めコンテンツ最大幅: `1000px`
- PC / Tablet の左右余白: `24px`
- Mobile の左右余白: `16px`
- 背景は画面幅いっぱいに表示し、コンテンツのみ最大幅を設定する。

```scss
.l-container {
  width: 100%;
  max-width: $container-width;
  margin-inline: auto;
  padding-inline: $side-padding;
  box-sizing: border-box;
}

.l-container--narrow {
  width: 100%;
  max-width: $container-width-narrow;
  margin-inline: auto;
  padding-inline: $side-padding;
  box-sizing: border-box;
}

@media (max-width: $breakpoint-mobile) {
  .l-container,
  .l-container--narrow {
    padding-inline: $side-padding-mobile;
  }
}
```

### Section Spacing

セクション間の余白は以下を基本とします。

| Size | PC | Tablet | Mobile |
| --- | --- | --- | --- |
| Large | `100px` | `80px` | `60px` |
| Small | `50px` | `40px` | `32px` |

原則としてセクション間の余白は `margin-top` で管理してください。

```scss
section + section {
  margin-top: $section-space-lg;
}

.section--spacing-sm {
  margin-top: $section-space-sm;
}

@media (max-width: $breakpoint-tablet) {
  section + section {
    margin-top: $section-space-lg-tablet;
  }

  .section--spacing-sm {
    margin-top: $section-space-sm-tablet;
  }
}

@media (max-width: $breakpoint-mobile) {
  section + section {
    margin-top: $section-space-lg-mobile;
  }

  .section--spacing-sm {
    margin-top: $section-space-sm-mobile;
  }
}
```

- 特別な理由がない限り、独自のセクション間余白を追加しない。
- 上下両方に同じ余白を設定して、余白が二重にならないようにする。

---

## Responsive

### Breakpoints

- PC: `1024px` 以上
- Tablet: `768px - 1023px`
- Mobile: `767px` 以下

### Layout Rules

- PCの横並びレイアウトをMobileで無理に維持しない。
- Tabletでは必要に応じて2カラムに変更する。
- Mobileではカードなどの主要コンテンツは原則1カラムとする。
- 横スクロールが発生しないレイアウトにする。
- 独自のブレークポイントを追加せず、原則として定義済みの値を使用する。