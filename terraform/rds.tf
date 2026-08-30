# ==========================================
# Database (RDS PostgreSQL)
# ==========================================

# DB サブネットグループ（プライベートサブネット2つを指定）
resource "aws_db_subnet_group" "main" {
  name        = "${var.project_name}-db-subnet-group"
  description = "DB subnet group for PostgreSQL"
  subnet_ids  = [aws_subnet.private_1a.id, aws_subnet.private_1c.id]

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# RDS PostgreSQL インスタンス
resource "aws_db_instance" "postgres" {
  identifier            = "${var.project_name}-db"
  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  engine                = "postgres"
  engine_version        = "15"
  instance_class        = var.rds_instance_class

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # セキュリティ設定: パブリックアクセス無効、EC2からのみアクセス可能
  publicly_accessible = false
  multi_az            = false # コスト最小化のため単一AZ

  # 削除保護・スナップショット設定（開発・検証時はtrueで素早く破棄可能）
  skip_final_snapshot = true

  auto_minor_version_upgrade = true
  backup_retention_period   = 7 # 自動バックアップ（7日間保持）

  tags = {
    Name = "${var.project_name}-postgres"
  }
}
