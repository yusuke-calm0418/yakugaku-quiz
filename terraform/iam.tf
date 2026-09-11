resource "aws_ssm_parameter" "app" {
  for_each = toset(["SECRET_KEY", "DB_PASSWORD", "DB_HOST", "DB_NAME", "DB_USER", "DB_PORT"])
  name     = "/${var.project_name}/${var.environment}/${each.key}"
  type     = "SecureString"
  value = {
    SECRET_KEY  = var.django_secret_key
    DB_PASSWORD = var.db_password
    DB_HOST     = aws_db_instance.postgres.address
    DB_NAME     = var.db_name
    DB_USER     = var.db_username
    DB_PORT     = "5432"
  }[each.key]
}

resource "aws_iam_role" "web" {
  name = "${var.project_name}-web"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_instance_profile" "web" {
  name = "${var.project_name}-web"
  role = aws_iam_role.web.name
}

resource "aws_iam_role_policy" "web" {
  role = aws_iam_role.web.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["ssm:GetParameter", "ssm:GetParameters"], Resource = [for p in aws_ssm_parameter.app : p.arn] },
      { Effect = "Allow", Action = ["ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"], Resource = "*" },
      { Effect = "Allow", Action = "ssm:UpdateInstanceInformation", Resource = "*" },
      { Effect = "Allow", Action = "s3:ListBucket", Resource = aws_s3_bucket.assets.arn, Condition = { StringLike = { "s3:prefix" = ["static/*", "media/*"] } } },
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = ["${aws_s3_bucket.assets.arn}/static/*", "${aws_s3_bucket.assets.arn}/media/*"] }
    ]
  })
}
