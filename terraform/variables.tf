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
  description = "ARM64対応EC2インスタンスタイプ"
  type        = string
  default     = "t4g.micro"
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

variable "domain_name" {
  description = "公開用FQDN（末尾のドットなし）"
  type        = string
}

variable "hosted_zone_id" {
  description = "既存のRoute 53パブリックホストゾーンID"
  type        = string
}

variable "django_secret_key" {
  type      = string
  sensitive = true
}

variable "holiday_dates" {
  description = "停止する日本の祝日・振替休日 YYYY-MM-DD。毎年更新する"
  type        = set(string)
  validation {
    condition     = alltrue([for date in var.holiday_dates : can(formatdate("YYYY-MM-DD", "${date}T00:00:00Z"))])
    error_message = "祝日はYYYY-MM-DD形式の有効な日付を指定してください。"
  }
}

variable "holiday_calendar_year" {
  description = "祝日リストの対象年。年が一致しない場合は自動起動せずエラーを記録する"
  type        = number
}

variable "budget_email" {
  description = "予算通知先メールアドレス"
  type        = string
}

variable "budget_usd_jpy" {
  description = "予算の円換算に使用する1 USDあたりの円。実際の請求為替とは異なるため随時見直す"
  type        = number
  validation {
    condition     = var.budget_usd_jpy > 0
    error_message = "正の換算レートを指定してください。"
  }
}
