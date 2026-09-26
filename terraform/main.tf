terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # 本番運用時は S3 バックエンドで tfstate を管理することを推奨します
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "yakugaku-quiz/terraform.tfstate"
  #   region = "ap-northeast-1"
  # }
}

provider "aws" {
  region = var.aws_region

  # MiniStack用ダミー認証情報
  access_key = "test"
  secret_key = "test"

  # 本物のAWSへの認証チェックを無効化
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    ec2        = "http://localhost:4566"
    rds        = "http://localhost:4566"
    s3         = "http://localhost:4566"
    route53    = "http://localhost:4566"
    ssm        = "http://localhost:4566"
    iam        = "http://localhost:4566"
    sts        = "http://localhost:4566"
    cloudwatch = "http://localhost:4566"
    logs       = "http://localhost:4566"
    lambda     = "http://localhost:4566"
    events     = "http://localhost:4566"
    budgets    = "http://localhost:4566"
    scheduler  = "http://localhost:4566"
  }

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }

}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  # MiniStack用ダミー認証情報
  access_key = "test"
  secret_key = "test"

  # 本物のAWSへの認証チェックを無効化
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    ec2        = "http://localhost:4566"
    rds        = "http://localhost:4566"
    acm        = "http://localhost:4566"
    s3         = "http://localhost:4566"
    route53    = "http://localhost:4566"
    cloudfront = "http://localhost:4566"
    ssm        = "http://localhost:4566"
    iam        = "http://localhost:4566"
    sts        = "http://localhost:4566"
  }
}

data "aws_caller_identity" "current" {}
