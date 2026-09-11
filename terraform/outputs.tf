output "rds_endpoint" {
  description = "RDS PostgreSQLのエンドポイントアドレス"
  value       = aws_db_instance.postgres.endpoint
}

output "rds_address" {
  description = "RDSホスト名（.envのDB_HOSTに指定）"
  value       = aws_db_instance.postgres.address
}

output "s3_bucket_name" {
  description = "静的・メディアファイル用S3バケット名"
  value       = aws_s3_bucket.assets.id
}

output "site_url" {
  value = "https://${var.domain_name}"
}

output "ec2_instance_id" {
  value = aws_instance.web.id
}

output "scheduler_function_name" {
  value = aws_lambda_function.schedule.function_name
}
