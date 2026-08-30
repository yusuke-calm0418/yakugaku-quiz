output "ec2_public_ip" {
  description = "EC2インスタンスのElastic IP（固定パブリックIP）"
  value       = aws_eip.web.public_ip
}

output "ec2_ssh_command" {
  description = "SSH接続コマンド例"
  value       = "ssh -i <your-key.pem> ec2-user@${aws_eip.web.public_ip}"
}

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
