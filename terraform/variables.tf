variable "aws_region" {
  description = "AWSリージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "project_name" {
  description = "プロジェクト名"
  type        = string
  default     = "yakugaku-quiz"
}

variable "environment" {
  description = "環境名（dev, stg, prodなど）"
  type        = string
  default     = "prod"
}

variable "ec2_instance_type" {
  description = "EC2インスタンスタイプ（無料利用枠・低コスト用: t3.micro または t4g.small）"
  type        = string
  default     = "t3.micro"
}

variable "ec2_key_name" {
  description = "SSH接続用のAWSキーペア名（未設定時はキーなしで作成）"
  type        = string
  default     = ""
}

variable "allowed_ssh_cidr" {
  description = "SSH接続を許可するCIDRブロック（例: 自身の固定IP/32）"
  type        = string
  default     = "0.0.0.0/0"
}

variable "rds_instance_class" {
  description = "RDSインスタンスクラス"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_name" {
  description = "初期作成するデータベース名"
  type        = string
  default     = "yakugaku_quiz"
}

variable "db_username" {
  description = "RDSのマスターユーザー名"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "RDSのマスターパスワード"
  type        = string
  sensitive   = true
}
