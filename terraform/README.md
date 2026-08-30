# yakugaku-quiz Terraform インフラ管理

このディレクトリは、**yakugaku-quiz** の AWS インフラ（パターンB：EC2 + RDS + S3 + VPC）を管理する Terraform コードです。

---

## 構成リソース概要

- **VPC & ネットワーク** (`vpc.tf`):
  - 1 VPC (`10.0.0.0/16`)
  - パブリックサブネット × 2 (`10.0.1.0/24`, `10.0.2.0/24`)
  - プライベートサブネット × 2 (`10.0.11.0/24`, `10.0.12.0/24`)
  - インターネットゲートウェイ & ルートテーブル
- **セキュリティ** (`security_group.tf`):
  - `EC2 SG`: 80(HTTP), 443(HTTPS), 22(SSH)
  - `RDS SG`: 5432(PostgreSQL) を EC2 SG からのみ許可
- **コンピュート** (`ec2.tf`):
  - Amazon Linux 2023 (`t3.micro` または `t4g.small`)
  - 固定IP（Elastic IP）
  - 初期化スクリプトによる Docker & Docker Compose の自動インストール
- **データベース** (`rds.tf`):
  - Amazon RDS for PostgreSQL 15 (`db.t4g.micro`)
  - 自動バックアップ & ストレージ自動拡張 (20GB〜50GB)
- **ストレージ** (`s3.tf`):
  - 静的・メディアアセット用 S3 バケット

---

## 前提条件

1. [Terraform CLI (>= 1.5.0)](https://developer.hashicorp.com/terraform/downloads) がインストールされていること
2. [AWS CLI](https://aws.amazon.com/cli/) がインストールされ、認証情報が設定されていること
   ```bash
   aws configure
   ```
3. AWSマネジメントコンソールで SSH接続用の **キーペア（Key Pair）** を作成済みであること

---

## インフラ構築手順

### 1. 変数ファイルの設定

設定サンプルをコピーして `terraform.tfvars` を作成し、必要な値を設定します。

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` を開き、以下を編集します：
- `ec2_key_name`: 作成したキーペア名
- `db_password`: データベースの管理者パスワード
- `allowed_ssh_cidr`: SSHアクセスを許可するIPアドレス（推奨: `自身のグローバルIP/32`）

### 2. 初期化 (init)

```bash
terraform init
```

### 3. 事前確認 (plan)

作成されるリソースの一覧と差分を確認します。

```bash
terraform plan
```

### 4. リソース作成 (apply)

```bash
terraform apply
```

確認プロンプトが表示されたら `yes` を入力して適用します（RDS作成を含め約5〜10分かかります）。

適用完了後、ターミナルに以下のような出力が表示されます：
- `ec2_public_ip`: EC2の固定パブリックIP
- `rds_address`: RDSのホストアドレス
- `s3_bucket_name`: S3バケット名

---

## Djangoアプリケーションとの接続

EC2上のDjango環境変数（`.env`）に以下のように設定します：

```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=<ec2_public_ip>,your-domain.com

DB_ENGINE=django.db.backends.postgresql
DB_NAME=yakugaku_quiz
DB_USER=postgres
DB_PASSWORD=<設定したパスワード>
DB_HOST=<outputsで出力された rds_address>
DB_PORT=5432
```

---

## インフラの削除 (destroy)

検証終了時などにリソースをすべて削除する場合は以下を実行します：

```bash
terraform destroy
```
