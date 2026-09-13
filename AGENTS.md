# yakugaku-quiz
薬剤師国家試験対策向けの Django 製クイズWebアプリケーションです。

## Project Documentation
プロジェクト仕様・機能仕様については以下を参照してください。
- `docs/project-spec.md`

## Feature Specifications
個別機能を新規作成・修正する場合は、該当する機能仕様を確認する。
- 問題CSVインポート: `docs/product-specs/question-csv-import.md`
- 問題画像表示: `docs/product-specs/question-image-support.md`
機能仕様と既存実装に差異がある場合は、既存コードと `docs/project-spec.md` を確認したうえで整合性を保つこと。

## Development Rules
コードの新規作成・修正時は以下を参照してください。
- `docs/agent/development.md`

## Design Rules
HTML / SCSS / UIを変更する場合は、以下を必ず参照してください。
- `docs/agent/design.md`

## Infrastructure Rules
AWS、ネットワーク、本番用Docker、デプロイ、Terraformを変更する場合は、以下を必ず参照してください。

- `docs/project-spec.md の「AWSインフラ構成」`
- `docs/agent/infrastructure.md`

## Chat Output
ユーザーへの作業報告は以下に従ってください。
- `docs/agent/chat-output.md`

## Tech Stack
- Python 3.12
- Django
- PostgreSQL
- Docker / Docker Compose
- HTML / JavaScript / SCSS

## Important
- 既存コード・既存設計を確認してから変更する。
- 大規模な仕様変更やDB設計変更は独断で行わない。
- 機能仕様を変更する場合は `docs/project-spec.md` との整合性を確認する。