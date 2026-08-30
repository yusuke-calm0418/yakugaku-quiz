# ==========================================
# Storage (Amazon S3)
# ==========================================

# S3バケット名重複防止のための一意サフィックス
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# 静的ファイル・画像保存用 S3 バケット
resource "aws_s3_bucket" "assets" {
  bucket        = "${var.project_name}-assets-${random_id.bucket_suffix.hex}"
  force_destroy = false

  tags = {
    Name = "${var.project_name}-assets"
  }
}

# バケットバージョニング（誤削除・上書き防止）
resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

# パブリックアクセスブロック設定
resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
